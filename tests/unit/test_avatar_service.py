import pytest

from sidebrain_back.models.avatar_model import Avatar
from sidebrain_back.services.avatar_service import AvatarService


class AvatarRepositoryDouble:
    def __init__(self) -> None:
        self.active = Avatar(
            avt_slug="cat",
            avt_name="Gato",
            avt_image_path="/static/avatars/cat.png",
            avt_is_active=True,
        )
        self.inactive = Avatar(
            avt_slug="fox",
            avt_name="Raposa",
            avt_image_path="/static/avatars/fox.png",
            avt_is_active=False,
        )

    async def list_active(self):
        return [self.active]

    async def get(self, slug: str):
        return {"cat": self.active, "fox": self.inactive}.get(slug)

    async def get_active(self, slug: str):
        avatar = await self.get(slug)
        return avatar if avatar and avatar.avt_is_active else None


@pytest.mark.anyio
async def test_avatar_service_lists_active_and_resolves_default():
    service = AvatarService(AvatarRepositoryDouble())

    catalog = await service.list_active()
    selected = await service.resolve("cat")
    default = await service.resolve(None)
    inactive = await service.resolve("fox")

    assert [item.slug for item in catalog.data] == ["cat"]
    assert selected.image_url == "/static/avatars/cat.png"
    assert default.slug == "default"
    assert inactive.slug == "default"


@pytest.mark.anyio
async def test_avatar_service_rejects_inactive_selection_lookup():
    service = AvatarService(AvatarRepositoryDouble())

    assert await service.get_active("fox") is None
    assert await service.get_active("missing") is None
