from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.avatar_model import Avatar
from sidebrain_back.repositories.avatar_repository import (
    AvatarRepository,
    get_avatar_repository,
)
from sidebrain_back.schemas.avatar_schema import (
    AvatarListResponse,
    AvatarResponse,
)

DEFAULT_AVATAR = AvatarResponse(
    slug="default",
    name="Avatar padrão",
    image_url="/static/avatars/default.png",
)


class AvatarService:
    def __init__(
        self,
        repository: AvatarRepository,
        _db: AsyncSession | None = None,
    ) -> None:
        self.repository = repository

    async def list_active(self) -> AvatarListResponse:
        avatars = await self.repository.list_active()
        return AvatarListResponse(
            data=[self.to_response(avatar) for avatar in avatars]
        )

    async def get_active(self, slug: str) -> Avatar | None:
        return await self.repository.get_active(slug)

    async def resolve(self, slug: str | None) -> AvatarResponse:
        if slug is None:
            return DEFAULT_AVATAR
        avatar = await self.repository.get(slug)
        if avatar is None or not avatar.avt_is_active:
            return DEFAULT_AVATAR
        return self.to_response(avatar)

    @staticmethod
    def to_response(avatar: Avatar) -> AvatarResponse:
        return AvatarResponse(
            slug=avatar.avt_slug,
            name=avatar.avt_name,
            image_url=avatar.avt_image_path,
        )


def get_avatar_service(
    repository: AvatarRepository = Depends(get_avatar_repository),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AvatarService:
    return AvatarService(repository, db)
