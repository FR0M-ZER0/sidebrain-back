from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from sidebrain_back.core.rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.user_schema import PasswordUpdateRequest
from sidebrain_back.services.auth_errors import (
    AuthenticationError,
    DomainValidationError,
)
from sidebrain_back.services.user_service import UserService


class DbDouble:
    def __init__(self, events=None, commit_error=None):
        self.commits = 0
        self.rollbacks = 0
        self.events = events
        self.commit_error = commit_error

    async def commit(self):
        if self.events is not None:
            self.events.append("commit")
        if self.commit_error is not None:
            raise self.commit_error
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class RepositoryDouble:
    def __init__(self, user, events=None):
        self.user = user
        self.updated = None
        self.events = events

    async def get_for_update(self, _user_id):
        return self.user

    async def update_password(self, user, password_hash):
        if self.events is not None:
            self.events.append("update")
        self.updated = password_hash
        user.usr_password_hash = password_hash
        user.usr_token_version += 1


class LimiterDouble:
    def __init__(self, events=None, success_error=None):
        self.calls = []
        self.events = events
        self.success_error = success_error

    async def check(self, *key):
        self.calls.append(("check", key))

    async def record_failure(self, *key):
        self.calls.append(("failure", key))

    async def record_success(self, *key):
        self.calls.append(("success", key))
        if self.events is not None:
            self.events.append("success")
        if self.success_error is not None:
            raise self.success_error


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


@pytest.mark.anyio
async def test_password_success_revalidates_limit_before_commit(monkeypatch):
    monkeypatch.setattr(
        "sidebrain_back.services.user_service.verify_password",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "sidebrain_back.services.user_service.hash_password",
        AsyncMock(return_value="hash-novo"),
    )
    events = []
    user = _user()
    service = UserService(
        RepositoryDouble(user, events),
        DbDouble(events),
        LimiterDouble(events),
    )

    await service.update_password(
        user,
        PasswordUpdateRequest(
            currentPassword="senha-antiga",
            newPassword="senha-nova",
        ),
        "origin",
    )

    assert events == ["update", "success", "commit"]


@pytest.mark.anyio
async def test_failed_password_commit_rolls_back_after_limiter_revalidation(
    monkeypatch,
):
    monkeypatch.setattr(
        "sidebrain_back.services.user_service.verify_password",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "sidebrain_back.services.user_service.hash_password",
        AsyncMock(return_value="hash-novo"),
    )
    events = []
    user = _user()
    db = DbDouble(events, commit_error=RuntimeError("commit failed"))
    limiter = LimiterDouble(events)
    service = UserService(RepositoryDouble(user, events), db, limiter)

    with pytest.raises(RuntimeError, match="commit failed"):
        await service.update_password(
            user,
            PasswordUpdateRequest(
                currentPassword="senha-antiga",
                newPassword="senha-nova",
            ),
            "origin",
        )

    assert events == ["update", "success", "commit"]
    assert db.rollbacks == 1


@pytest.mark.anyio
async def test_password_change_rolls_back_if_limiter_is_unavailable(
    monkeypatch,
):
    monkeypatch.setattr(
        "sidebrain_back.services.user_service.verify_password",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "sidebrain_back.services.user_service.hash_password",
        AsyncMock(return_value="hash-novo"),
    )
    user = _user()
    db = DbDouble()
    limiter = LimiterDouble(
        success_error=RateLimitUnavailable("redis unavailable")
    )
    service = UserService(RepositoryDouble(user), db, limiter)

    with pytest.raises(RateLimitUnavailable):
        await service.update_password(
            user,
            PasswordUpdateRequest(
                currentPassword="senha-antiga",
                newPassword="senha-nova",
            ),
            "origin",
        )

    assert db.commits == 0
    assert db.rollbacks == 1
    assert any(call[0] == "success" for call in limiter.calls)


@pytest.mark.anyio
async def test_password_change_rolls_back_if_concurrent_failures_arm_lock(
    monkeypatch,
):
    monkeypatch.setattr(
        "sidebrain_back.services.user_service.verify_password",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "sidebrain_back.services.user_service.hash_password",
        AsyncMock(return_value="hash-novo"),
    )
    user = _user()
    db = DbDouble()
    limiter = LimiterDouble(success_error=RateLimitExceeded(900))
    service = UserService(RepositoryDouble(user), db, limiter)

    with pytest.raises(RateLimitExceeded):
        await service.update_password(
            user,
            PasswordUpdateRequest(
                currentPassword="senha-antiga",
                newPassword="senha-nova",
            ),
            "origin",
        )

    assert db.commits == 0
    assert db.rollbacks == 1
