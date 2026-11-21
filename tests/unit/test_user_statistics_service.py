from datetime import date, datetime
from uuid import uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.day_streak_model import DayStreak
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.ranking_repository import RankedUserRow
from sidebrain_back.schemas.user_statistics_schema import (
    UserStatisticsResponse,
)
from sidebrain_back.services.user_statistics_service import (
    UserStatisticsService,
)


class RankingRepositoryDouble:
    def __init__(self, row: RankedUserRow | None) -> None:
        self.row = row

    async def get_user_ranking(self, user_id):
        return self.row


class UserStatisticsRepositoryDouble:
    def __init__(self, badge_count: int = 0, streak: DayStreak | None = None):
        self.badge_count = badge_count
        self.streak = streak

    async def count_unlocked_badges(self, user_id):
        return self.badge_count

    async def get_day_streak(self, user_id):
        return self.streak


@pytest.mark.anyio
async def test_get_user_statistics_uses_ranking_and_progress_values():
    user_id = uuid4()
    ranking = RankedUserRow(
        position=2,
        user_id=user_id,
        name="Aluno",
        xp=250,
        missions_completed=3,
    )
    service = UserStatisticsService(
        RankingRepositoryDouble(ranking),
        UserStatisticsRepositoryDouble(badge_count=4),
    )

    result = await service.get_user_statistics(User(usr_id=user_id))

    assert result == UserStatisticsResponse(
        xp=250,
        missions_completed=3,
        position=2,
        badges_unlocked=4,
        current_day_streak=0,
    )


@pytest.mark.anyio
async def test_get_user_statistics_returns_not_found_for_unranked_user():
    service = UserStatisticsService(
        RankingRepositoryDouble(None),
        UserStatisticsRepositoryDouble(),
    )

    with pytest.raises(ProblemDetailError) as exc_info:
        await service.get_user_statistics(User(usr_id=uuid4()))

    assert exc_info.value.status_code == 404
    assert exc_info.value.title == "Não encontrado"


@pytest.mark.parametrize(
    "last_active_day,expected",
    [
        (date(2026, 11, 18), 6),
        (date(2026, 11, 17), 6),
        (date(2026, 11, 16), 0),
        (date(2026, 11, 19), 0),
    ],
)
def test_current_day_streak_uses_today_and_yesterday_in_utc(
    last_active_day, expected
):
    streak = DayStreak(
        dst_value=6,
        dst_updated_at=datetime.combine(last_active_day, datetime.min.time()),
    )

    result = UserStatisticsService._get_current_day_streak(
        streak, date(2026, 11, 18)
    )

    assert result == expected


def test_current_day_streak_is_zero_without_a_record():
    assert (
        UserStatisticsService._get_current_day_streak(None, date(2026, 11, 18))
        == 0
    )
