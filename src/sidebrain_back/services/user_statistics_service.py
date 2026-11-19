from datetime import UTC, date, datetime, timedelta

from fastapi import Depends

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.day_streak_model import DayStreak
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.ranking_repository import (
    RankingRepository,
    get_ranking_repository,
)
from sidebrain_back.repositories.user_statistics_repository import (
    UserStatisticsRepository,
    get_user_statistics_repository,
)
from sidebrain_back.schemas.user_statistics_schema import (
    UserStatisticsResponse,
)


class UserStatisticsService:
    def __init__(
        self,
        ranking_repository: RankingRepository,
        repository: UserStatisticsRepository,
    ) -> None:
        self.ranking_repository = ranking_repository
        self.repository = repository

    async def get_user_statistics(self, user: User) -> UserStatisticsResponse:
        ranking = await self.ranking_repository.get_user_ranking(user.usr_id)
        if ranking is None:
            raise ProblemDetailError(
                404,
                "Não encontrado",
                "Usuário não encontrado.",
            )

        badges_unlocked = await self.repository.count_unlocked_badges(
            user.usr_id
        )
        day_streak = await self.repository.get_day_streak(user.usr_id)
        current_day_streak = self._get_current_day_streak(
            day_streak, datetime.now(UTC).date()
        )

        return UserStatisticsResponse(
            xp=ranking.xp,
            missions_completed=ranking.missions_completed,
            position=ranking.position,
            badges_unlocked=badges_unlocked,
            current_day_streak=current_day_streak,
        )

    @staticmethod
    def _get_current_day_streak(
        streak: DayStreak | None, today_utc: date
    ) -> int:
        if streak is None:
            return 0

        last_active_day = streak.dst_updated_at.date()
        if last_active_day not in (
            today_utc,
            today_utc - timedelta(days=1),
        ):
            return 0
        return streak.dst_value


def get_user_statistics_service(
    ranking_repository: RankingRepository = Depends(  # noqa: B008
        get_ranking_repository
    ),
    repository: UserStatisticsRepository = Depends(  # noqa: B008
        get_user_statistics_repository
    ),
) -> UserStatisticsService:
    return UserStatisticsService(ranking_repository, repository)
