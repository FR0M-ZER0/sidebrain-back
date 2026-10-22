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
        xp_expr = func.coalesce(func.sum(Mission.msn_xp_reward), 0).label("xp")
        missions_expr = func.count(Mission.msn_id).label("missions_completed")

        stmt = (
            select(
                User.usr_id,
                User.usr_name,
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
            .order_by(
                desc(xp_expr),
                User.usr_created_at.asc(),
                User.usr_id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            RankedUserRow(
                position=offset + idx + 1,
                user_id=row.usr_id,
                name=row.usr_name,
                xp=row.xp,
                missions_completed=row.missions_completed,
            )
            for idx, row in enumerate(rows)
        ]

    async def get_user_ranking(self, user_id: UUID) -> RankedUserRow | None:
        xp_expr = func.coalesce(func.sum(Mission.msn_xp_reward), 0).label("xp")
        missions_expr = func.count(Mission.msn_id).label("missions_completed")

        ranked_subq = (
            select(
                User.usr_id.label("user_id"),
                User.usr_name.label("name"),
                xp_expr,
                missions_expr,
                func.row_number()
                .over(
                    order_by=(
                        desc(xp_expr),
                        User.usr_created_at.asc(),
                        User.usr_id.asc(),
                    )
                )
                .label("position"),
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
            .cte("ranked_users")
        )

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


def get_ranking_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> RankingRepository:
    return RankingRepository(db)
