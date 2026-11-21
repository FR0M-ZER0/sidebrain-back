from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.mission_progress_status_enum import (
    MissionProgressStatusEnum,
)
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.mission_progress_model import MissionProgress
from sidebrain_back.models.user_model import User


@dataclass(frozen=True)
class RankedUserRow:
    position: int
    user_id: UUID
    name: str
    xp: int
    missions_completed: int


@dataclass(frozen=True)
class UserXpSummary:
    xp: int
    missions_completed: int


class RankingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def count_ranked_users(self) -> int:
        stmt = select(func.count(User.usr_id)).where(
            User.usr_is_deleted.is_(False)
        )
        return (await self.db.scalar(stmt)) or 0

    async def list_rankings(
        self, offset: int, limit: int
    ) -> list[RankedUserRow]:
        summary = self._ranking_summary().subquery("ranking_summary")
        position_expr = (
            func.row_number()
            .over(
                order_by=(
                    desc(summary.c.xp),
                    summary.c.created_at.asc(),
                    summary.c.user_id.asc(),
                )
            )
            .label("position")
        )
        stmt = (
            select(
                position_expr,
                summary.c.user_id,
                summary.c.name,
                summary.c.xp,
                summary.c.missions_completed,
            )
            .order_by(position_expr)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            RankedUserRow(
                position=row.position,
                user_id=row.user_id,
                name=row.name,
                xp=row.xp,
                missions_completed=row.missions_completed,
            )
            for row in rows
        ]

    async def get_user_ranking(self, user_id: UUID) -> RankedUserRow | None:
        summary = self._ranking_summary().subquery("ranking_summary")
        position_expr = (
            func.row_number()
            .over(
                order_by=(
                    desc(summary.c.xp),
                    summary.c.created_at.asc(),
                    summary.c.user_id.asc(),
                )
            )
            .label("position")
        )
        ranked_subq = select(
            summary.c.user_id,
            summary.c.name,
            summary.c.xp,
            summary.c.missions_completed,
            position_expr,
        ).cte("ranked_users")

        stmt = select(
            ranked_subq.c.position,
            ranked_subq.c.user_id,
            ranked_subq.c.name,
            ranked_subq.c.xp,
            ranked_subq.c.missions_completed,
        ).where(ranked_subq.c.user_id == user_id)

        result = await self.db.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None

        return RankedUserRow(
            position=row.position,
            user_id=row.user_id,
            name=row.name,
            xp=row.xp,
            missions_completed=row.missions_completed,
        )

    async def get_user_xp_summary(self, user_id: UUID) -> UserXpSummary | None:
        summary = self._ranking_summary().subquery("ranking_summary")
        row = await self.db.execute(
            select(summary.c.xp, summary.c.missions_completed).where(
                summary.c.user_id == user_id
            )
        )
        result = row.one_or_none()
        if result is None:
            return None
        return UserXpSummary(
            xp=result.xp,
            missions_completed=result.missions_completed,
        )

    @staticmethod
    def _ranking_summary():
        xp_expr = func.coalesce(func.sum(Mission.msn_xp_reward), 0).label("xp")
        missions_expr = func.count(Mission.msn_id).label("missions_completed")
        return (
            select(
                User.usr_id.label("user_id"),
                User.usr_name.label("name"),
                User.usr_created_at.label("created_at"),
                xp_expr,
                missions_expr,
            )
            .outerjoin(
                MissionProgress,
                (MissionProgress.mpg_user_id == User.usr_id)
                & (
                    MissionProgress.mpg_status
                    == MissionProgressStatusEnum.DONE
                ),
            )
            .outerjoin(
                Mission,
                (Mission.msn_id == MissionProgress.mpg_mission_id)
                & Mission.msn_is_deleted.is_(False),
            )
            .where(User.usr_is_deleted.is_(False))
            .group_by(User.usr_id, User.usr_name, User.usr_created_at)
        )


def get_ranking_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> RankingRepository:
    return RankingRepository(db)
