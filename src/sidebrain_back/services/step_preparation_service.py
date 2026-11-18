from uuid import UUID, uuid4

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track
from sidebrain_back.repositories.step_preparation_repository import (
    StepPreparationRepository,
)


class StepPreparationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = StepPreparationRepository(db)

    async def reserve(
        self,
        source_step_id: UUID,
        target_step_id: UUID,
        user_id: UUID | None = None,
    ) -> str:
        row = (
            await self.db.execute(
                select(Track.trk_id, Track.trk_user_id)
                .join(Step, Step.stp_track_id == Track.trk_id)
                .where(
                    Step.stp_id == source_step_id,
                    Step.stp_is_deleted.is_(False),
                    Track.trk_is_deleted.is_(False),
                    *(
                        (Track.trk_user_id == user_id,)
                        if user_id is not None
                        else ()
                    ),
                )
            )
        ).one()
        task_id = str(uuid4())
        await self.repository.create(
            task_id=task_id,
            user_id=row.trk_user_id,
            track_id=row.trk_id,
            source_step_id=source_step_id,
            target_step_id=target_step_id,
        )
        await self.db.commit()
        return task_id

    async def finish(self, task_id: str, status: str) -> bool:
        changed = await self.repository.finish(task_id, status)
        if changed:
            await self.db.commit()
        return changed


def get_step_preparation_service(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> StepPreparationService:
    return StepPreparationService(db)
