from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.models.generation_request_model import GenerationRequest
from sidebrain_back.models.knowledge_assessment_model import (
    KnowledgeAssessment,
)
from sidebrain_back.models.knowledge_assessment_question_model import (
    KnowledgeAssessmentQuestion,
)
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.step_preparation_model import StepPreparation
from sidebrain_back.models.step_summary_generation_model import (
    StepSummaryGeneration,
)
from sidebrain_back.models.track_model import Track
from sidebrain_back.models.user_model import User


class JobUpdateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def active_user(self, user_id: UUID) -> bool:
        return bool(
            await self.db.scalar(
                select(User.usr_id).where(
                    User.usr_id == user_id,
                    User.usr_is_deleted.is_(False),
                )
            )
        )

    async def track_generation(
        self, request_id: UUID, user_id: UUID
    ) -> GenerationRequest | None:
        request = await self.db.scalar(
            select(GenerationRequest).where(
                GenerationRequest.request_id == request_id,
                GenerationRequest.user_id == user_id,
            )
        )
        if request is None:
            return None
        if request.track_id is not None:
            accessible = await self.db.scalar(
                select(Track.trk_id).where(
                    Track.trk_id == request.track_id,
                    Track.trk_user_id == user_id,
                    Track.trk_is_deleted.is_(False),
                )
            )
            if accessible is None:
                return None
        return request

    async def assessment(
        self, assessment_id: UUID, user_id: UUID
    ) -> KnowledgeAssessment | None:
        result = await self.db.execute(
            select(KnowledgeAssessment)
            .where(
                KnowledgeAssessment.kas_id == assessment_id,
                KnowledgeAssessment.kas_user_id == user_id,
            )
            .options(
                selectinload(KnowledgeAssessment.questions).selectinload(
                    KnowledgeAssessmentQuestion.alternatives
                )
            )
        )
        return result.scalars().unique().one_or_none()

    async def step_preparation(
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

    async def step_summary(
        self, track_id: UUID, step_id: UUID, user_id: UUID
    ) -> tuple[Step, StepSummaryGeneration | None] | None:
        result = await self.db.execute(
            select(Step, StepSummaryGeneration)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .outerjoin(
                StepSummaryGeneration,
                StepSummaryGeneration.step_id == Step.stp_id,
            )
            .where(
                Track.trk_id == track_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
                Step.stp_id == step_id,
                Step.stp_track_id == track_id,
                Step.stp_is_deleted.is_(False),
            )
        )
        row = result.one_or_none()
        if row is None or (row[1] is None and row[0].stp_summary is None):
            return None
        return row[0], row[1]


def get_job_update_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> JobUpdateRepository:
    return JobUpdateRepository(db)
