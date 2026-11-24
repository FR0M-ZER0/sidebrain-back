from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.topic_alias_model import TopicAlias


class TopicAliasRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_by_alias(self, alias: str) -> TopicAlias | None:
        return await self.db.scalar(
            select(TopicAlias).where(
                TopicAlias.alias == alias,
                TopicAlias.is_active.is_(True),
            )
        )


def get_topic_alias_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TopicAliasRepository:
    return TopicAliasRepository(db)
