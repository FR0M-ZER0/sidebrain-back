from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.badge_progress_status_enum import (
    BadgeProgressStatusEnum,
)
from sidebrain_back.models.badge_model import Badge
from sidebrain_back.models.badge_progress_model import BadgeProgress
from sidebrain_back.models.day_streak_model import DayStreak


class UserStatisticsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def count_unlocked_badges(self, user_id: UUID) -> int:
        statement = (
            select(func.count(BadgeProgress.bpg_id))
            .join(Badge, Badge.bdg_id == BadgeProgress.bpg_badge_id)
            .where(
                BadgeProgress.bpg_user_id == user_id,
                BadgeProgress.bpg_status == BadgeProgressStatusEnum.DONE,
                Badge.bdg_is_deleted.is_(False),
            )
        )
        return (await self.db.scalar(statement)) or 0

    async def get_day_streak(self, user_id: UUID) -> DayStreak | None:
        statement = select(DayStreak).where(
            DayStreak.dst_user_id == user_id
        )
        return await self.db.scalar(statement)


def get_user_statistics_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UserStatisticsRepository:
    return UserStatisticsRepository(db)
