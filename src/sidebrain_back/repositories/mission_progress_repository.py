from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.models.answer_model import Answer
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.mission_progress_model import MissionProgress
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track


@dataclass(frozen=True)
class LessonProgressFacts:
    step_id: UUID
    lesson_id: UUID | None
    quizzes: int
    answered: int
    correct: int


class MissionProgressRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_track_by_step_for_update(
        self, user_id: UUID, step_id: UUID
    ) -> UUID | None:
        return await self.db.scalar(
            select(Track.trk_id)
            .join(Step, Step.stp_track_id == Track.trk_id)
            .where(
                Step.stp_id == step_id,
                Step.stp_is_deleted.is_(False),
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
            .with_for_update(of=Track)
        )

    async def get_track_by_quiz_for_update(
        self, user_id: UUID, quiz_id: UUID
    ) -> UUID | None:
        return await self.db.scalar(
            select(Track.trk_id)
            .join(Step, Step.stp_track_id == Track.trk_id)
            .join(Lesson, Lesson.lsn_step_id == Step.stp_id)
            .join(Quiz, Quiz.qui_lesson_id == Lesson.lsn_id)
            .where(
                Quiz.qui_id == quiz_id,
                Quiz.qui_is_deleted.is_(False),
                Lesson.lsn_is_deleted.is_(False),
                Step.stp_is_deleted.is_(False),
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
            .with_for_update(of=Track)
        )

    async def get_learning_facts(
        self,
        user_id: UUID,
        track_id: UUID,
        correct_rates: tuple[AnswerRateEnum, ...],
    ) -> list[LessonProgressFacts]:
        answers = (
            select(
                Answer.ans_question_id.label("quiz_id"),
                func.bool_or(Answer.ans_rate.in_(correct_rates)).label(
                    "correct"
                ),
            )
            .where(Answer.ans_user_id == user_id)
            .group_by(Answer.ans_question_id)
            .subquery()
        )
        rows = await self.db.execute(
            select(
                Step.stp_id,
                Lesson.lsn_id,
                func.count(Quiz.qui_id),
                func.count(answers.c.quiz_id),
                func.count(answers.c.quiz_id).filter(answers.c.correct),
            )
            .join(Track, Track.trk_id == Step.stp_track_id)
            .outerjoin(
                Lesson,
                (Lesson.lsn_step_id == Step.stp_id)
                & Lesson.lsn_is_deleted.is_(False),
            )
            .outerjoin(
                Quiz,
                (Quiz.qui_lesson_id == Lesson.lsn_id)
                & Quiz.qui_is_deleted.is_(False),
            )
            .outerjoin(answers, answers.c.quiz_id == Quiz.qui_id)
            .where(
                Track.trk_id == track_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
                Step.stp_is_deleted.is_(False),
            )
            .group_by(Step.stp_id, Lesson.lsn_id)
        )
        return [LessonProgressFacts(*row) for row in rows]

    async def list_missions_by_track_id(
        self, user_id: UUID, track_id: UUID
    ) -> list[Mission]:
        result = await self.db.scalars(
            select(Mission)
            .join(Step, Step.stp_id == Mission.msn_step_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Track.trk_id == track_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
                Step.stp_is_deleted.is_(False),
                Mission.msn_is_deleted.is_(False),
            )
            .options(
                selectinload(
                    Mission.mission_progresses.and_(
                        MissionProgress.mpg_user_id == user_id
                    )
                )
            )
            .execution_options(populate_existing=True)
        )
        return list(result.all())

    async def create(self, progress: MissionProgress) -> None:
        self.db.add(progress)

    async def flush(self) -> None:
        await self.db.flush()


def get_mission_progress_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MissionProgressRepository:
    return MissionProgressRepository(db)
