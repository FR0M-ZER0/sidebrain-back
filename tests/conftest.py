from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from sidebrain_back.core.auth import get_current_user
from sidebrain_back.core.database import get_db
from sidebrain_back.models.user_model import User


@pytest.fixture
def authenticated_user() -> User:
    return User(
        usr_id=uuid4(),
        usr_email="test@example.com",
        usr_name="Test User",
        usr_password_hash="test-hash",
        usr_is_deleted=False,
    )


@pytest.fixture
def async_session() -> AsyncSession:
    return AsyncSession()


@pytest.fixture
def dependency_overrides(
    async_session: AsyncSession, authenticated_user: User
) -> dict:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield async_session

    async def override_current_user() -> User:
        return authenticated_user

    return {
        get_db: override_get_db,
        get_current_user: override_current_user,
    }


@pytest.fixture
def test_app(dependency_overrides: dict) -> FastAPI:
    app.dependency_overrides.update(dependency_overrides)
    yield app
    app.dependency_overrides.clear()
