from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.rate_limit import (
    AuthRateLimiter,
    get_auth_rate_limiter,
)
from sidebrain_back.core.security import (
    TokenValidationError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.user_repository import (
    UserRepository,
    get_user_repository,
)
from sidebrain_back.schemas.auth_schema import AuthResponse, UserLoginRequest
from sidebrain_back.schemas.user_schema import (
    UserRegisterRequest,
    UserResponse,
)
from sidebrain_back.services.auth_errors import (
    AuthenticationError,
    ConflictError,
)

_EMAIL_CONSTRAINTS = {
    "user_usr_email_key",
    "uq_user_usr_email_normalized",
}


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        db: AsyncSession,
        rate_limiter: AuthRateLimiter | None = None,
    ) -> None:
        self.repository = repository
        self.db = db
        self.rate_limiter = rate_limiter

    async def authenticate_user_token(self, token: str) -> User:
        try:
            claims = decode_access_token(token)
        except TokenValidationError as error:
            raise AuthenticationError("Credencial inválida.") from error

        user = await self.repository.get(claims.user_id)
        if user is None or user.usr_token_version != claims.token_version:
            raise AuthenticationError("Credencial inválida.")
        return user

    async def register_user(
        self,
        payload: UserRegisterRequest,
    ) -> AuthResponse:
        email = str(payload.email)
        if await self.repository.email_exists(email):
            raise ConflictError("O e-mail informado já está em uso.")

        try:
            password_hash = await hash_password(payload.password)
            user = await self.repository.create(
                payload.name,
                email,
                password_hash,
            )
            await self.db.commit()
        except IntegrityError as error:
            await self.db.rollback()
            if _is_email_unique_violation(error):
                raise ConflictError(
                    "O e-mail informado já está em uso."
                ) from error
            raise
        except Exception:
            await self.db.rollback()
            raise

        return self._auth_response(user)

    async def login_user(
        self,
        payload: UserLoginRequest,
        origin: str,
    ) -> AuthResponse:
        limiter = self._require_rate_limiter()
        email = str(payload.email)
        key = ("login", email, origin)
        await limiter.check(*key)

        user = await self.repository.get_by_email(email)
        if user is None:
            await verify_dummy_password(payload.password)
            await limiter.record_failure(*key)
            raise AuthenticationError("Credenciais inválidas.")

        if not await verify_password(payload.password, user.usr_password_hash):
            await limiter.record_failure(*key)
            raise AuthenticationError("Credenciais inválidas.")

        await limiter.record_success(*key)
        return self._auth_response(user)

    def _require_rate_limiter(self) -> AuthRateLimiter:
        if self.rate_limiter is None:
            raise RuntimeError("Limitador de autenticação não configurado.")
        return self.rate_limiter

    @staticmethod
    def _auth_response(user: User) -> AuthResponse:
        return AuthResponse(
            accessToken=create_access_token(
                user.usr_id,
                user.usr_token_version,
            ),
            user=UserResponse.model_validate(user),
        )


def _is_email_unique_violation(error: IntegrityError) -> bool:
    candidate = error.orig
    while candidate is not None:
        sqlstate = getattr(candidate, "sqlstate", None) or getattr(
            candidate,
            "pgcode",
            None,
        )
        constraint = getattr(candidate, "constraint_name", None)
        diagnostic = getattr(candidate, "diag", None)
        if diagnostic is not None:
            constraint = constraint or getattr(
                diagnostic,
                "constraint_name",
                None,
            )
        if sqlstate == "23505" and constraint in _EMAIL_CONSTRAINTS:
            return True
        candidate = getattr(candidate, "__cause__", None)
    return False


def get_auth_service(
    repository: UserRepository = Depends(get_user_repository),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    rate_limiter: AuthRateLimiter = Depends(get_auth_rate_limiter),  # noqa: B008
) -> AuthService:
    return AuthService(repository, db, rate_limiter)
