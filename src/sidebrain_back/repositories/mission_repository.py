from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.mission_criteria_enum import MissionCriteriaEnum
from sidebrain_back.enums.mission_difficulty_enum import MissionDifficultyEnum
from sidebrain_back.enums.mission_progress_status_enum import (
    MissionProgressStatusEnum,
)
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.mission_progress_model import MissionProgress
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track


@dataclass(frozen=True)
class MissionListRow:
    mission: Mission
    step_title: str
    track_id: UUID
    track_title: str
    track_icon: str | None
    status: MissionProgressStatusEnum
    score: int
    last_activity_at: datetime


class MissionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(
        self,
        user_id: UUID,
        offset: int,
        limit: int,
        *,
        status: MissionProgressStatusEnum | None = None,
        track_id: UUID | None = None,
        difficulty: MissionDifficultyEnum | None = None,
        criteria: MissionCriteriaEnum | None = None,
        q: str | None = None,
        sort: str = "recent",
    ) -> tuple[list[MissionListRow], int]:
        progress_status = func.coalesce(
            MissionProgress.mpg_status, MissionProgressStatusEnum.IDLE
        )
        activity = func.greatest(
            Mission.msn_updated_at,
            func.coalesce(
                MissionProgress.mpg_updated_at, Mission.msn_updated_at
            ),
        )
        filters = [
            Track.trk_user_id == user_id,
            Track.trk_is_deleted.is_(False),
            Step.stp_is_deleted.is_(False),
            Mission.msn_is_deleted.is_(False),
        ]
        if status is not None:
            filters.append(progress_status == status)
        if track_id is not None:
            filters.append(Track.trk_id == track_id)
        if difficulty is not None:
            filters.append(Mission.msn_difficulty == difficulty)
        if criteria is not None:
            filters.append(Mission.msn_criteria == criteria)
        if q is not None:
            escaped = (
                q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            filters.append(
                Mission.msn_title.ilike(f"%{escaped}%", escape="\\")
            )
        base = (
            select(
                Mission,
                Step.stp_title,
                Track.trk_id,
                Track.trk_title,
                Track.trk_icon,
                progress_status,
                func.coalesce(MissionProgress.mpg_score, 0),
                activity,
            )
            .join(Step, Step.stp_id == Mission.msn_step_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .outerjoin(
                MissionProgress,
                (MissionProgress.mpg_mission_id == Mission.msn_id)
                & (MissionProgress.mpg_user_id == user_id),
            )
            .where(*filters)
        )
        total = await self.db.scalar(
            select(func.count()).select_from(base.subquery())
        )
        ordering = (
            (activity.asc(), Mission.msn_id.asc())
            if sort == "oldest"
            else (activity.desc(), Mission.msn_id.desc())
        )
        rows = await self.db.execute(
            base.order_by(*ordering)
            .offset(offset)
            .limit(limit)
            .options(self._progress_options(user_id))
        )
        return [MissionListRow(*row) for row in rows], int(total or 0)

    async def get_accessible_step(
        self, user_id: UUID, step_id: UUID
    ) -> Step | None:
        return await self.db.scalar(
            select(Step)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Step.stp_id == step_id,
                Step.stp_is_deleted.is_(False),
                Track.trk_is_deleted.is_(False),
                Track.trk_user_id == user_id,
            )
        )

    async def create(
        self,
        step_id: UUID,
        title: str,
        difficulty: MissionDifficultyEnum,
        xp_reward: int,
        criteria: MissionCriteriaEnum,
        criteria_value: int,
    ) -> Mission:
        mission = Mission(
            msn_step_id=step_id,
            msn_title=title,
            msn_difficulty=difficulty,
            msn_xp_reward=xp_reward,
            msn_criteria=criteria,
            msn_criteria_value=criteria_value,
            msn_is_deleted=False,
            msn_deleted_at=None,
            mission_progresses=[],
        )
        self.db.add(mission)
        await self.db.flush()
        return mission

    async def get(self, user_id: UUID, mission_id: UUID) -> Mission | None:
        result = await self.db.execute(
            select(Mission)
            .join(Step, Step.stp_id == Mission.msn_step_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Mission.msn_id == mission_id,
                Mission.msn_is_deleted.is_(False),
                Step.stp_is_deleted.is_(False),
                Track.trk_is_deleted.is_(False),
                Track.trk_user_id == user_id,
            )
            .options(self._progress_options(user_id))
        )
        return result.scalars().unique().one_or_none()

    async def list_by_step_id(
        self,
        user_id: UUID,
        step_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[Mission], int]:
        filters = (
            Mission.msn_step_id == step_id,
            Mission.msn_is_deleted.is_(False),
            Step.stp_id == step_id,
            Step.stp_is_deleted.is_(False),
            Track.trk_is_deleted.is_(False),
            Track.trk_user_id == user_id,
        )
        base = (
            select(Mission)
            .join(Step, Step.stp_id == Mission.msn_step_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(*filters)
        )
        total = await self.db.scalar(
            select(func.count()).select_from(base.subquery())
        )
        result = await self.db.execute(
            base.order_by(Mission.msn_updated_at.desc(), Mission.msn_id.desc())
            .offset(offset)
            .limit(limit)
            .options(self._progress_options(user_id))
        )
        return list(result.scalars().unique().all()), int(total or 0)

    async def update(
        self,
        mission: Mission,
        values: dict[str, object],
    ) -> Mission:
        for field, value in values.items():
            setattr(mission, f"msn_{field}", value)
        mission.msn_updated_at = datetime.now(UTC).replace(tzinfo=None)
        await self.db.flush()
        return mission

    async def soft_delete(self, mission: Mission) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        mission.msn_is_deleted = True
        mission.msn_deleted_at = now
        mission.msn_updated_at = now
        await self.db.flush()

    @staticmethod
    def _progress_options(user_id: UUID):
        return selectinload(
            Mission.mission_progresses.and_(
                MissionProgress.mpg_user_id == user_id
            )
        )


def get_mission_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MissionRepository:
    return MissionRepository(db)
