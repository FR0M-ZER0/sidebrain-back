from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.avatar_model import Avatar


class AvatarRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(self) -> list[Avatar]:
        result = await self.db.scalars(
            select(Avatar)
            .where(Avatar.avt_is_active.is_(True))
            .order_by(Avatar.avt_slug)
        )
        return list(result.all())

    async def get_active(self, slug: str) -> Avatar | None:
        return await self.db.scalar(
            select(Avatar).where(
                Avatar.avt_slug == slug,
                Avatar.avt_is_active.is_(True),
            )
        )

    async def get(self, slug: str) -> Avatar | None:
        return await self.db.scalar(
            select(Avatar).where(Avatar.avt_slug == slug)
        )


def get_avatar_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AvatarRepository:
    return AvatarRepository(db)
