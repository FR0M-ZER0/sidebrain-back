from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.avatar_schema import AvatarResponse
from sidebrain_back.schemas.user_schema import UserUpdateRequest
from sidebrain_back.services.auth_errors import DomainValidationError
from sidebrain_back.services.user_service import UserService


class UserRepositoryDouble:
    def __init__(self, user: User) -> None:
        self.user = user
        self.updated_avatar = "not-called"

    async def get_for_update(self, _user_id):
        return self.user

    async def email_exists(self, _email, _user_id):
        return False

    async def update(
        self,
        user,
        name,
        email,
        *,
        avatar_slug=None,
        update_avatar=False,
    ):
        if name is not None:
            user.usr_name = name
        if email is not None:
            user.usr_email = email
        if update_avatar:
            self.updated_avatar = avatar_slug
            user.usr_avatar_slug = avatar_slug


class RankingRepositoryDouble:
    async def get_user_xp_summary(self, _user_id):
        return SimpleNamespace(xp=0, missions_completed=0)


class AvatarServiceDouble:
    async def get_active(self, slug):
        return object() if slug == "cat" else None

    async def resolve(self, slug):
        return AvatarResponse(
            slug=slug or "default",
            name="Gato" if slug else "Avatar padrão",
            image_url=f"/static/avatars/{slug or 'default'}.png",
        )


@pytest.mark.anyio
async def test_user_service_selects_and_removes_avatar_without_other_changes():
    user = User(
        usr_id=uuid4(),
        usr_name="Maria",
        usr_email="maria@example.com",
        usr_password_hash="hash",
        usr_is_deleted=False,
        usr_created_at=datetime(2026, 1, 1),
    )
    repository = UserRepositoryDouble(user)
    db = SimpleNamespace(
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    service = UserService(
        repository,
        db,
        ranking_repository=RankingRepositoryDouble(),
        avatar_service=AvatarServiceDouble(),
    )

    selected = await service.update_user(user, UserUpdateRequest(avatar="cat"))
    removed = await service.update_user(user, UserUpdateRequest(avatar=None))

    assert selected.avatar.slug == "cat"
    assert removed.avatar.slug == "default"
    assert user.usr_name == "Maria"
    assert user.usr_email == "maria@example.com"
    assert repository.updated_avatar is None


@pytest.mark.anyio
async def test_user_service_rejects_unavailable_avatar_without_update():
    user = User(
        usr_id=uuid4(),
        usr_name="Maria",
        usr_email="maria@example.com",
        usr_password_hash="hash",
        usr_is_deleted=False,
        usr_created_at=datetime(2026, 1, 1),
    )
    repository = UserRepositoryDouble(user)
    db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    service = UserService(
        repository,
        db,
        ranking_repository=RankingRepositoryDouble(),
        avatar_service=AvatarServiceDouble(),
    )

    with pytest.raises(DomainValidationError):
        await service.update_user(user, UserUpdateRequest(avatar="fox"))

    assert repository.updated_avatar == "not-called"
    db.rollback.assert_awaited_once()
