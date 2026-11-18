from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.step_summary_generation_model import (
    StepSummaryGeneration,
)


class StepSummaryGenerationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def reserve(self, step_id: UUID) -> int:
        statement = (
            insert(StepSummaryGeneration)
            .values(step_id=step_id, generation=1, status="pending")
            .on_conflict_do_update(
                index_elements=[StepSummaryGeneration.step_id],
                set_={
                    "generation": StepSummaryGeneration.generation + 1,
                    "status": "pending",
                },
            )
            .returning(StepSummaryGeneration.generation)
        )
        return int(await self.db.scalar(statement))

    async def get(
        self, step_id: UUID
    ) -> StepSummaryGeneration | None:
        return await self.db.get(StepSummaryGeneration, step_id)

    async def finish(
        self, step_id: UUID, generation: int, status: str
    ) -> bool:
        current = await self.db.scalar(
            select(StepSummaryGeneration)
            .where(StepSummaryGeneration.step_id == step_id)
            .with_for_update()
        )
        if (
            current is None
            or current.generation != generation
            or current.status != "pending"
        ):
            return False
        current.status = status
        await self.db.flush()
        return True


def get_step_summary_generation_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> StepSummaryGenerationRepository:
    return StepSummaryGenerationRepository(db)
