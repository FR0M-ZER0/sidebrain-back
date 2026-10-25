from uuid import UUID

from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.answer_model import Answer
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track


class StepSummaryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_step_id_by_quiz_id(
        self, user_id: UUID, quiz_id: UUID
    ) -> UUID | None:
        return await self.db.scalar(
            select(Step.stp_id)
            .join(Lesson, Lesson.lsn_step_id == Step.stp_id)
            .join(Quiz, Quiz.qui_lesson_id == Lesson.lsn_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Quiz.qui_id == quiz_id,
                Quiz.qui_is_deleted.is_(False),
                Lesson.lsn_is_deleted.is_(False),
                Step.stp_is_deleted.is_(False),
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
        )

    async def list_reasons_by_step_id(
        self, user_id: UUID, step_id: UUID
    ) -> list[str | None]:
        result = await self.db.scalars(
            select(Answer.ans_reason)
            .join(Quiz, Quiz.qui_id == Answer.ans_question_id)
            .join(Lesson, Lesson.lsn_id == Quiz.qui_lesson_id)
            .join(Step, Step.stp_id == Lesson.lsn_step_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Step.stp_id == step_id,
                Step.stp_is_deleted.is_(False),
                Lesson.lsn_is_deleted.is_(False),
                Quiz.qui_is_deleted.is_(False),
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
                Answer.ans_user_id == user_id,
                Answer.ans_reason.is_not(None),
            )
            .order_by(Answer.ans_created_at.asc(), Answer.ans_id.asc())
        )
        return list(result.all())

    async def update_summary(self, step_id: UUID, summary: str) -> None:
        await self.db.execute(
            update(Step)
            .where(Step.stp_id == step_id)
            .values(stp_summary=summary)
        )


def get_step_summary_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> StepSummaryRepository:
    return StepSummaryRepository(db)
