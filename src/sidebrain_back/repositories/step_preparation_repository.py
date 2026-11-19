from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.step_preparation_model import StepPreparation
from sidebrain_back.models.track_model import Track


class StepPreparationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        task_id: str,
        user_id: UUID,
        track_id: UUID,
        source_step_id: UUID,
        target_step_id: UUID,
    ) -> StepPreparation:
        preparation = StepPreparation(
            task_id=task_id,
            user_id=user_id,
            track_id=track_id,
            source_step_id=source_step_id,
            target_step_id=target_step_id,
            status="pending",
        )
        self.db.add(preparation)
        await self.db.flush()
        return preparation

    async def get(self, task_id: str) -> StepPreparation | None:
        return await self.db.get(StepPreparation, task_id)

    async def get_accessible(
        self, task_id: str, user_id: UUID
    ) -> StepPreparation | None:
        return await self.db.scalar(
            select(StepPreparation)
            .join(Track, Track.trk_id == StepPreparation.track_id)
            .join(Step, Step.stp_id == StepPreparation.target_step_id)
            .where(
                StepPreparation.task_id == task_id,
                StepPreparation.user_id == user_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
                Step.stp_is_deleted.is_(False),
                (
                    StepPreparation.finished_at.is_(None)
                    | (
                        StepPreparation.finished_at
                        > func.clock_timestamp() - text("interval '24 hours'")
                    )
                ),
            )
        )

    async def finish(self, task_id: str, status: str) -> bool:
        preparation = await self.db.scalar(
            select(StepPreparation)
            .where(StepPreparation.task_id == task_id)
            .with_for_update()
        )
        if preparation is None or preparation.status != "pending":
            return False
        preparation.status = status
        preparation.finished_at = datetime.now(UTC)
        await self.db.flush()
        return True


def get_step_preparation_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> StepPreparationRepository:
    return StepPreparationRepository(db)
