from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from sidebrain_back.core.constants import Env
from sidebrain_back.core.security import (
    TokenValidationError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.mark.anyio
async def test_hash_password_uses_argon2id_and_verifies_password():
    password_hash = await hash_password("senha-segura")

    assert password_hash.startswith("$argon2id$")
    assert await verify_password("senha-segura", password_hash)
    assert not await verify_password("senha-incorreta", password_hash)


@pytest.mark.parametrize(
    "secret",
    [
        "segredo-curto",
        "a" * 32,
        "SUBSTITUA_COM_UM_SEGREDO_ALEATORIO",
        " segredo-com-diversidade-suficiente-123! ",
    ],
)
def test_jwt_secret_configuration_rejects_weak_values(secret):
    with pytest.raises(ValidationError):
        type(Env)(JWT_SECRET_KEY=secret)


def test_access_token_has_required_claims_and_sixty_minute_lifetime():
    user_id = uuid4()
    token = create_access_token(user_id, 7)
    raw = jwt.decode(token, Env.JWT_SECRET_KEY, algorithms=["HS256"])
    claims = decode_access_token(token)

    assert raw["sub"] == str(user_id)
    assert raw["ver"] == 7
    assert raw["exp"] - raw["iat"] == 60 * 60
    assert claims.user_id == user_id
    assert claims.token_version == 7


@pytest.mark.parametrize(
    "token_factory",
    [
        lambda: str(uuid4()),
        lambda: create_access_token(uuid4(), 0) + "alterado",
        lambda: jwt.encode(
            {
                "sub": str(uuid4()),
                "iat": datetime.now(UTC) - timedelta(hours=2),
                "exp": datetime.now(UTC) - timedelta(hours=1),
                "ver": 0,
            },
            Env.JWT_SECRET_KEY,
            algorithm="HS256",
        ),
        lambda: jwt.encode(
            {
                "sub": str(uuid4()),
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            Env.JWT_SECRET_KEY,
            algorithm="HS256",
        ),
        lambda: jwt.encode(
            {
                "sub": str(uuid4()),
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "ver": True,
            },
            Env.JWT_SECRET_KEY,
            algorithm="HS256",
        ),
    ],
)
def test_decode_rejects_invalid_or_incomplete_credentials(token_factory):
    with pytest.raises(TokenValidationError):
        decode_access_token(token_factory())
