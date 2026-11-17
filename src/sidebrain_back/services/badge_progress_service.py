from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.badge_criteria_enum import BadgeCriteriaEnum
from sidebrain_back.enums.badge_progress_status_enum import (
    BadgeProgressStatusEnum,
)
from sidebrain_back.models.badge_progress_model import BadgeProgress
from sidebrain_back.models.day_streak_model import DayStreak
from sidebrain_back.repositories.badge_progress_repository import (
    BadgeActivityStats,
    BadgeLearningFact,
    BadgeProgressRepository,
    get_badge_progress_repository,
)


class BadgeProgressService:
    CORRECT_RATES = (AnswerRateEnum.GOOD, AnswerRateEnum.PERFECT)

    def __init__(self, repository: BadgeProgressRepository, db: AsyncSession):
        self.repository = repository
        self.db = db

    @staticmethod
    def _next_streak(value: int, last_active: date, today: date) -> int:
        if last_active >= today:
            return value
        if last_active == today - timedelta(days=1):
            return value + 1
        return 1

    async def register_activity_and_update_badges(
        self, user_id: UUID
    ) -> BadgeActivityStats:
        """Update daily activity and badges in the caller's transaction."""
        if not await self.repository.lock_user(user_id):
            raise ProblemDetailError(
                404, "Não encontrado", "Usuário não encontrado."
            )

        now = datetime.now(UTC).replace(tzinfo=None)
        streak = await self.repository.get_day_streak(user_id)
        if streak is None:
            await self.repository.create_day_streak(
                DayStreak(dst_user_id=user_id, dst_value=1, dst_updated_at=now)
            )
        else:
            streak.dst_value = self._next_streak(
                streak.dst_value, streak.dst_updated_at.date(), now.date()
            )
            streak.dst_updated_at = now

        return await self.update_badges_by_user_id(user_id, now=now)

    async def update_badges_by_user_id(
        self, user_id: UUID, *, now: datetime | None = None
    ) -> BadgeActivityStats:
        if not await self.repository.lock_user(user_id):
            raise ProblemDetailError(
                404, "Não encontrado", "Usuário não encontrado."
            )
        now = now or datetime.now(UTC).replace(tzinfo=None)
        facts = await self.repository.get_learning_facts(
            user_id, self.CORRECT_RATES
        )
        stats = await self._build_stats(user_id, facts)
        badges = await self.repository.get_badges_by_user(user_id)
        for badge in badges:
            progress = next(
                (
                    item
                    for item in badge.badge_progresses
                    if item.bpg_user_id == user_id
                ),
                None,
            )
            if (
                progress is not None
                and progress.bpg_status == BadgeProgressStatusEnum.DONE
            ):
                continue
            current = self._criteria_value(
                BadgeCriteriaEnum(badge.bdg_criteria), stats
            )
            status = (
                BadgeProgressStatusEnum.DONE
                if current >= badge.bdg_criteria_value
                else BadgeProgressStatusEnum.IN_PROGRESS
                if current > 0
                else BadgeProgressStatusEnum.IDLE
            )
            if progress is None:
                progress = BadgeProgress(
                    bpg_user_id=user_id,
                    bpg_badge_id=badge.bdg_id,
                    bpg_status=status,
                )
                badge.badge_progresses.append(progress)
                await self.repository.add_progress(progress)
            elif progress.bpg_status != status:
                progress.bpg_status = status
                progress.bpg_updated_at = now
        await self.repository.flush()
        return stats

    async def recalculate_badges_by_user_id(self, user_id: UUID) -> None:
        try:
            await self.update_badges_by_user_id(user_id)
            await self.db.commit()
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500,
                "Erro interno",
                "Não foi possível atualizar o progresso dos badges.",
            ) from error

    async def _build_stats(
        self, user_id: UUID, facts: list[BadgeLearningFact]
    ) -> BadgeActivityStats:
        tracks: dict[UUID, dict[UUID, list[BadgeLearningFact]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for fact in facts:
            if fact.step_id is not None:
                tracks[fact.track_id][fact.step_id].append(fact)
            else:
                tracks.setdefault(fact.track_id, defaultdict(list))

        lessons_completed = 0
        right_answers = 0
        completed_tracks = 0
        for steps in tracks.values():
            track_is_complete = bool(steps)
            for lessons in steps.values():
                active_lessons = [
                    item for item in lessons if item.lesson_id is not None
                ]
                step_is_complete = bool(active_lessons)
                for lesson in active_lessons:
                    is_complete = (
                        lesson.quizzes > 0
                        and lesson.answered == lesson.quizzes
                    )
                    lessons_completed += int(is_complete)
                    right_answers += lesson.correct
                    step_is_complete &= is_complete
                track_is_complete &= step_is_complete
            completed_tracks += int(track_is_complete)

        (
            xp_gained,
            missions_completed,
        ) = await self.repository.get_mission_rewards(user_id)
        tracks_created = await self.repository.get_created_track_count(user_id)
        streak = await self.repository.get_day_streak(user_id)
        return BadgeActivityStats(
            xp_gained=xp_gained,
            missions_completed=missions_completed,
            tracks_created=tracks_created,
            tracks_completed=completed_tracks,
            lessons_completed=lessons_completed,
            right_answers=right_answers,
            day_streak=streak.dst_value if streak is not None else 0,
        )

    @staticmethod
    def _criteria_value(
        criteria: BadgeCriteriaEnum, stats: BadgeActivityStats
    ) -> int:
        return {
            BadgeCriteriaEnum.XP_GAINED: stats.xp_gained,
            BadgeCriteriaEnum.TRACKS_COMPLETED: stats.tracks_completed,
            BadgeCriteriaEnum.LESSONS_COMPLETED: stats.lessons_completed,
            BadgeCriteriaEnum.RIGHT_ANSWERS: stats.right_answers,
            BadgeCriteriaEnum.DAY_STREAK: stats.day_streak,
            BadgeCriteriaEnum.TRACKS_CREATED: stats.tracks_created,
            BadgeCriteriaEnum.MISSIONS_COMPLETED: stats.missions_completed,
        }[criteria]


def get_badge_progress_service(
    repository: BadgeProgressRepository = Depends(  # noqa: B008
        get_badge_progress_repository
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> BadgeProgressService:
    return BadgeProgressService(repository, db)
