from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.auth_schema import UserLoginRequest
from sidebrain_back.services.auth_errors import AuthenticationError
from sidebrain_back.services.auth_service import AuthService


class DbDouble:
    async def rollback(self):
        pass


class RepositoryDouble:
    def __init__(self, user=None):
        self.user = user

    async def get_by_email(self, _email):
        return self.user


class LimiterDouble:
    def __init__(self):
        self.calls = []

    async def check(self, *key):
        self.calls.append(("check", key))

    async def record_failure(self, *key):
        self.calls.append(("failure", key))

    async def record_success(self, *key):
        self.calls.append(("success", key))


@pytest.mark.anyio
@pytest.mark.parametrize("user", [None, "deleted", "wrong-password"])
async def test_login_has_same_error_for_unknown_deleted_or_wrong_password(
    monkeypatch,
    user,
):
    record = None
    if user != "deleted" and user is not None:
        record = User(
            usr_id=uuid4(),
            usr_name="Maria",
            usr_email="maria@example.com",
            usr_password_hash="hash",
            usr_token_version=0,
            usr_is_deleted=False,
        )
    verify = AsyncMock(return_value=False)
    dummy = AsyncMock()
    monkeypatch.setattr(
        "sidebrain_back.services.auth_service.verify_password", verify
    )
    monkeypatch.setattr(
        "sidebrain_back.services.auth_service.verify_dummy_password", dummy
    )
    limiter = LimiterDouble()
    service = AuthService(RepositoryDouble(record), DbDouble(), limiter)

    with pytest.raises(AuthenticationError, match="Credenciais inválidas"):
        await service.login_user(
            UserLoginRequest(
                email="maria@example.com", password="não registrar"
            ),
            "origin",
        )

    assert any(call[0] == "failure" for call in limiter.calls)
    if record is None:
        dummy.assert_awaited_once()


@pytest.mark.anyio
async def test_login_keeps_origins_in_separate_rate_limit_keys(monkeypatch):
    user = User(
        usr_id=uuid4(),
        usr_name="Maria",
        usr_email="maria@example.com",
        usr_password_hash="hash",
        usr_token_version=0,
        usr_is_deleted=False,
    )
    monkeypatch.setattr(
        "sidebrain_back.services.auth_service.verify_password",
        AsyncMock(return_value=True),
    )
    limiter = LimiterDouble()
    service = AuthService(RepositoryDouble(user), DbDouble(), limiter)
    payload = UserLoginRequest(
        email="maria@example.com", password="não registrar"
    )

    await service.login_user(payload, "origin-a")
    await service.login_user(payload, "origin-b")

    checks = [call[1][2] for call in limiter.calls if call[0] == "check"]
    assert checks == ["origin-a", "origin-b"]
