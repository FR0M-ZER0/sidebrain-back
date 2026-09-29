from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.models.answer_model import Answer
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

    async def create_answer(
        self,
        quiz_id: UUID,
        user_id: UUID,
        text: str,
        rate: AnswerRateEnum,
    ) -> Answer:
        answer = Answer(
            ans_question_id=quiz_id,
            ans_user_id=user_id,
            ans_text=text,
            ans_rate=rate,
        )
        self.db.add(answer)
        await self.db.flush()
        return answer

    async def complete_lesson_if_quizzes_answered(
        self, quiz_id: UUID, user_id: UUID
    ) -> UUID | None:
        lesson_context = await self.db.execute(
            select(Lesson.lsn_id, Lesson.lsn_step_id)
            .join(Quiz, Quiz.qui_lesson_id == Lesson.lsn_id)
            .where(Quiz.qui_id == quiz_id)
        )
        context = lesson_context.one_or_none()
        if context is None:
            return None

        lesson_id, step_id = context
        total_quizzes = int(
            await self.db.scalar(
                select(func.count())
                .select_from(Quiz)
                .where(
                    Quiz.qui_lesson_id == lesson_id,
                    Quiz.qui_is_deleted.is_(False),
                )
            )
            or 0
        )
        answered_quizzes = int(
            await self.db.scalar(
                select(func.count(func.distinct(Answer.ans_question_id)))
                .select_from(Answer)
                .join(Quiz, Quiz.qui_id == Answer.ans_question_id)
                .where(
                    Quiz.qui_lesson_id == lesson_id,
                    Quiz.qui_is_deleted.is_(False),
                    Answer.ans_user_id == user_id,
                )
            )
            or 0
        )
        if total_quizzes == 0 or answered_quizzes < total_quizzes:
            return None

        now = datetime.now(UTC).replace(tzinfo=None)
        await self.db.execute(
            update(Lesson)
            .where(Lesson.lsn_id == lesson_id)
            .values(
                lsn_status=LessonStatusEnum.DONE,
                lsn_updated_at=now,
            )
        )
        return step_id

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
