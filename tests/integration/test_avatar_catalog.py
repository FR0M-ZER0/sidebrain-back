import pytest
from sqlalchemy import select

from sidebrain_back.models.avatar_model import Avatar
from sidebrain_back.repositories.avatar_repository import AvatarRepository
from sidebrain_back.services.avatar_service import AvatarService


@pytest.mark.anyio
async def test_catalog_contains_initial_active_avatars(db_session):
    avatars = await AvatarRepository(db_session).list_active()

    assert {avatar.avt_slug for avatar in avatars} == {
        "cat",
        "dog",
        "fox",
        "bear",
        "rabbit",
        "panda",
        "owl",
        "penguin",
        "lion",
        "turtle",
    }


@pytest.mark.anyio
async def test_inactive_avatar_resolves_to_default(db_session):
    avatar = await db_session.scalar(
        select(Avatar).where(Avatar.avt_slug == "cat")
    )
    assert avatar is not None
    avatar.avt_is_active = False
    await db_session.flush()

    resolved = await AvatarService(AvatarRepository(db_session)).resolve("cat")

    assert resolved.slug == "default"
