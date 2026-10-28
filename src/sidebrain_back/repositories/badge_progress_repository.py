from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.models.answer_model import Answer
from sidebrain_back.models.badge_model import Badge
from sidebrain_back.models.badge_progress_model import BadgeProgress
from sidebrain_back.models.day_streak_model import DayStreak
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.mission_progress_model import MissionProgress
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track
from sidebrain_back.models.user_model import User


@dataclass(frozen=True)
class BadgeLearningFact:
    track_id: UUID
    step_id: UUID | None
    lesson_id: UUID | None
    quizzes: int
    answered: int
    correct: int


@dataclass(frozen=True)
class BadgeActivityStats:
    xp_gained: int
    missions_completed: int
    tracks_created: int
    tracks_completed: int
    lessons_completed: int
    right_answers: int
    day_streak: int


class BadgeProgressRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def lock_user(self, user_id: UUID) -> bool:
        result = await self.db.scalar(
            select(User.usr_id)
            .where(User.usr_id == user_id, User.usr_is_deleted.is_(False))
            .with_for_update()
        )
        return result is not None

    async def get_day_streak(self, user_id: UUID) -> DayStreak | None:
        return await self.db.scalar(
            select(DayStreak)
            .where(DayStreak.dst_user_id == user_id)
            .with_for_update()
        )

    async def create_day_streak(self, streak: DayStreak) -> None:
        self.db.add(streak)

    async def get_learning_facts(
        self, user_id: UUID, correct_rates: tuple[AnswerRateEnum, ...]
    ) -> list[BadgeLearningFact]:
        user_answers = (
            select(
                Answer.ans_question_id.label("quiz_id"),
                func.bool_or(Answer.ans_rate.in_(correct_rates)).label(
                    "is_correct"
                ),
            )
            .where(Answer.ans_user_id == user_id)
            .group_by(Answer.ans_question_id)
            .subquery()
        )
        rows = await self.db.execute(
            select(
                Track.trk_id,
                Step.stp_id,
                Lesson.lsn_id,
                func.count(Quiz.qui_id),
                func.count(user_answers.c.quiz_id),
                func.count(user_answers.c.quiz_id).filter(
                    user_answers.c.is_correct
                ),
            )
            .select_from(Track)
            .outerjoin(
                Step,
                (Step.stp_track_id == Track.trk_id)
                & Step.stp_is_deleted.is_(False),
            )
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
            .outerjoin(user_answers, user_answers.c.quiz_id == Quiz.qui_id)
            .where(
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
            .group_by(Track.trk_id, Step.stp_id, Lesson.lsn_id)
        )
        return [BadgeLearningFact(*row) for row in rows]

    async def get_created_track_count(self, user_id: UUID) -> int:
        return int(
            await self.db.scalar(
                select(func.count(Track.trk_id)).where(
                    Track.trk_user_id == user_id
                )
            )
            or 0
        )

    async def get_mission_rewards(self, user_id: UUID) -> tuple[int, int]:
        row = (
            await self.db.execute(
                select(
                    func.coalesce(func.sum(Mission.msn_xp_reward), 0),
                    func.count(Mission.msn_id),
                )
                .select_from(MissionProgress)
                .join(
                    Mission,
                    (Mission.msn_id == MissionProgress.mpg_mission_id)
                    & Mission.msn_is_deleted.is_(False),
                )
                .where(
                    MissionProgress.mpg_user_id == user_id,
                    MissionProgress.mpg_status == "done",
                )
            )
        ).one()
        return int(row[0] or 0), int(row[1] or 0)

    async def get_badges_by_user(self, user_id: UUID) -> list[Badge]:
        result = await self.db.scalars(
            select(Badge)
            .where(Badge.bdg_is_deleted.is_(False))
            .options(
                selectinload(
                    Badge.badge_progresses.and_(
                        BadgeProgress.bpg_user_id == user_id
                    )
                )
            )
            .execution_options(populate_existing=True)
        )
        return list(result.all())

    async def add_progress(self, progress: BadgeProgress) -> None:
        self.db.add(progress)

    async def flush(self) -> None:
        await self.db.flush()


def get_badge_progress_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> BadgeProgressRepository:
    return BadgeProgressRepository(db)
