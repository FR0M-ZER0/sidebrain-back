import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import PyJWTError
from pwdlib import PasswordHash

from sidebrain_back.core.constants import Env

_password_hash = PasswordHash.recommended()
_dummy_password_hash = _password_hash.hash("sidebrain-dummy-password")


class TokenValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: UUID
    token_version: int


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_password_hash.hash, password)


async def verify_password(password: str, password_hash: str) -> bool:
    try:
        return await asyncio.to_thread(
            _password_hash.verify,
            password,
            password_hash,
        )
    except (ValueError, TypeError):
        return False


async def verify_dummy_password(password: str) -> None:
    await verify_password(password, _dummy_password_hash)


def create_access_token(user_id: UUID, token_version: int) -> str:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=Env.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": issued_at,
            "exp": expires_at,
            "ver": token_version,
        },
        Env.JWT_SECRET_KEY,
        algorithm=Env.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            Env.JWT_SECRET_KEY,
            algorithms=[Env.JWT_ALGORITHM],
            options={"require": ["sub", "iat", "exp", "ver"]},
        )
        token_version = payload["ver"]
        if isinstance(token_version, bool) or not isinstance(
            token_version, int
        ):
            raise TokenValidationError("Versão da credencial inválida.")
        return AccessTokenClaims(
            user_id=UUID(payload["sub"]),
            token_version=token_version,
        )
    except (PyJWTError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, TokenValidationError):
            raise
        raise TokenValidationError("Credencial inválida.") from error
