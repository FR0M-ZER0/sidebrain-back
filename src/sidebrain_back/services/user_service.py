import logging

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.rate_limit import (
    AuthRateLimiter,
    RateLimitExceeded,
    RateLimitUnavailable,
    get_auth_rate_limiter,
)
from sidebrain_back.core.security import hash_password, verify_password
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.user_repository import (
    UserRepository,
    get_user_repository,
)
from sidebrain_back.schemas.user_schema import (
    PasswordUpdateRequest,
    UserResponse,
    UserUpdateRequest,
)
from sidebrain_back.services.auth_errors import (
    AuthenticationError,
    ConflictError,
    DomainValidationError,
    ResourceNotFoundError,
)
from sidebrain_back.services.auth_service import _is_email_unique_violation

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        db: AsyncSession,
        rate_limiter: AuthRateLimiter | None = None,
    ) -> None:
        self.repository = repository
        self.db = db
        self.rate_limiter = rate_limiter

    async def get_user(self, authenticated_user: User) -> UserResponse:
        user = await self.repository.get(authenticated_user.usr_id)
        if user is None:
            raise ResourceNotFoundError("Usuário não encontrado.")
        return UserResponse.model_validate(user)

    async def update_user(
        self,
        authenticated_user: User,
        payload: UserUpdateRequest,
    ) -> UserResponse:
        try:
            user = await self.repository.get_for_update(
                authenticated_user.usr_id
            )
            if user is None:
                raise ResourceNotFoundError("Usuário não encontrado.")

            email = str(payload.email) if payload.email is not None else None
            current_email = user.usr_email.strip().lower()
            if (
                email is not None
                and email != current_email
                and await self.repository.email_exists(email, user.usr_id)
            ):
                raise ConflictError("O e-mail informado já está em uso.")

            await self.repository.update(user, payload.name, email)
            response = UserResponse.model_validate(user)
            await self.db.commit()
            return response
        except (ConflictError, ResourceNotFoundError):
            await self.db.rollback()
            raise
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

    async def update_password(
        self,
        authenticated_user: User,
        payload: PasswordUpdateRequest,
        origin: str,
    ) -> None:
        limiter = self._require_rate_limiter()
        subject = str(authenticated_user.usr_id)
        key = ("password", subject, origin)
        await limiter.check(*key)
        try:
            user = await self.repository.get_for_update(
                authenticated_user.usr_id
            )
            if user is None:
                raise ResourceNotFoundError("Usuário não encontrado.")

            current_password_is_valid = await verify_password(
                payload.current_password,
                user.usr_password_hash,
            )
            if not current_password_is_valid:
                await limiter.record_failure(*key)
                raise AuthenticationError("Senha atual inválida.")
            if payload.new_password == payload.current_password:
                raise DomainValidationError(
                    "A nova senha deve ser diferente da senha atual."
                )

            password_hash = await hash_password(payload.new_password)
            await self.repository.update_password(user, password_hash)
            await self.db.commit()
        except (
            AuthenticationError,
            DomainValidationError,
            ResourceNotFoundError,
        ):
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

        try:
            await limiter.record_success(*key)
        except (RateLimitExceeded, RateLimitUnavailable):
            logger.warning(
                "Não foi possível limpar o limitador após a troca de senha; "
                "o contador foi mantido por segurança."
            )

    async def delete_user(self, authenticated_user: User) -> None:
        try:
            user = await self.repository.get_for_update(
                authenticated_user.usr_id
            )
            if user is None:
                raise ResourceNotFoundError("Usuário não encontrado.")
            await self.repository.delete(user)
            await self.db.commit()
        except ResourceNotFoundError:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

    def _require_rate_limiter(self) -> AuthRateLimiter:
        if self.rate_limiter is None:
            raise RuntimeError("Limitador de autenticação não configurado.")
        return self.rate_limiter


def get_user_service(
    repository: UserRepository = Depends(get_user_repository),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    rate_limiter: AuthRateLimiter = Depends(get_auth_rate_limiter),  # noqa: B008
) -> UserService:
    return UserService(repository, db, rate_limiter)
