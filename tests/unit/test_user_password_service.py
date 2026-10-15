from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.user_schema import PasswordUpdateRequest
from sidebrain_back.services.auth_errors import (
    AuthenticationError,
    DomainValidationError,
)
from sidebrain_back.services.user_service import UserService


class DbDouble:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class RepositoryDouble:
    def __init__(self, user):
        self.user = user
        self.updated = None

    async def get_for_update(self, _user_id):
        return self.user

    async def update_password(self, user, password_hash):
        self.updated = password_hash
        user.usr_password_hash = password_hash
        user.usr_token_version += 1


class LimiterDouble:
    def __init__(self):
        self.calls = []

    async def check(self, *key):
        self.calls.append(("check", key))

    async def record_failure(self, *key):
        self.calls.append(("failure", key))

    async def record_success(self, *key):
        self.calls.append(("success", key))


def _user():
    return User(
        usr_id=uuid4(),
        usr_name="Maria",
        usr_email="maria@example.com",
        usr_password_hash="hash-antigo",
        usr_token_version=2,
        usr_is_deleted=False,
    )


@pytest.mark.anyio
async def test_wrong_current_password_counts_failure_without_mutation(
    monkeypatch,
):
    monkeypatch.setattr(
        "sidebrain_back.services.user_service.verify_password",
        AsyncMock(return_value=False),
    )
    user = _user()
    repository = RepositoryDouble(user)
    limiter = LimiterDouble()
    db = DbDouble()
    service = UserService(repository, db, limiter)

    with pytest.raises(AuthenticationError):
        await service.update_password(
            user,
            PasswordUpdateRequest(
                currentPassword="errada", newPassword="nova-senha"
            ),
            "origin",
        )

    assert repository.updated is None
    assert any(call[0] == "failure" for call in limiter.calls)


@pytest.mark.anyio
async def test_equal_new_password_is_validation_error_without_counting(
    monkeypatch,
):
    monkeypatch.setattr(
        "sidebrain_back.services.user_service.verify_password",
        AsyncMock(return_value=True),
    )
    user = _user()
    limiter = LimiterDouble()
    service = UserService(RepositoryDouble(user), DbDouble(), limiter)

    with pytest.raises(DomainValidationError):
        await service.update_password(
            user,
            PasswordUpdateRequest(
                currentPassword="mesma-senha",
                newPassword="mesma-senha",
            ),
            "origin",
        )

    assert not any(call[0] == "failure" for call in limiter.calls)
