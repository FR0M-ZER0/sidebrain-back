from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track


class QuizRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_accessible_lesson(
        self,
        user_id: UUID,
        lesson_id: UUID,
    ) -> Lesson | None:
        result = await self.db.execute(
            select(Lesson)
            .join(Step, Step.stp_id == Lesson.lsn_step_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Lesson.lsn_id == lesson_id,
                Lesson.lsn_is_deleted.is_(False),
                Step.stp_is_deleted.is_(False),
                Track.trk_is_deleted.is_(False),
                Track.trk_user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, lesson_id: UUID, question: str) -> Quiz:
        quiz = Quiz(
            qui_lesson_id=lesson_id,
            qui_question=question,
            qui_is_deleted=False,
            qui_deleted_at=None,
            answers=[],
        )
        self.db.add(quiz)
        await self.db.flush()
        return quiz

    async def get_accessible_quiz(
        self,
        user_id: UUID,
        quiz_id: UUID,
    ) -> Quiz | None:
        result = await self.db.execute(
            select(Quiz)
            .join(Lesson, Lesson.lsn_id == Quiz.qui_lesson_id)
            .join(Step, Step.stp_id == Lesson.lsn_step_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .options(selectinload(Quiz.answers))
            .where(
                Quiz.qui_id == quiz_id,
                Quiz.qui_is_deleted.is_(False),
                Lesson.lsn_is_deleted.is_(False),
                Step.stp_is_deleted.is_(False),
                Track.trk_is_deleted.is_(False),
                Track.trk_user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_lesson_id(
        self,
        lesson_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[Quiz], int]:
        filters = (
            Quiz.qui_lesson_id == lesson_id,
            Quiz.qui_is_deleted.is_(False),
        )
        total = await self.db.scalar(
            select(func.count()).select_from(Quiz).where(*filters)
        )
        result = await self.db.execute(
            select(Quiz)
            .where(*filters)
            .options(selectinload(Quiz.answers))
            .order_by(Quiz.qui_updated_at.desc(), Quiz.qui_id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def update(self, quiz: Quiz, question: str) -> Quiz:
        quiz.qui_question = question
        quiz.qui_updated_at = datetime.now(UTC).replace(tzinfo=None)
        return quiz

    async def soft_delete(self, quiz: Quiz) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        quiz.qui_is_deleted = True
        quiz.qui_deleted_at = now
        quiz.qui_updated_at = now


def get_quiz_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> QuizRepository:
    return QuizRepository(db)
