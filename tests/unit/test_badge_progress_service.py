from datetime import date

import pytest

from sidebrain_back.enums.badge_criteria_enum import BadgeCriteriaEnum
from sidebrain_back.repositories.badge_progress_repository import (
    BadgeActivityStats,
)
from sidebrain_back.services.badge_progress_service import BadgeProgressService


@pytest.mark.parametrize(
    "criteria,attribute",
    [
        ("xp_gained", "xp_gained"),
        ("tracks_completed", "tracks_completed"),
        ("lessons_completed", "lessons_completed"),
        ("right_answers", "right_answers"),
        ("day_streak", "day_streak"),
        ("tracks_created", "tracks_created"),
        ("missions_completed", "missions_completed"),
    ],
)
def test_badge_criteria_read_the_corresponding_user_stat(criteria, attribute):
    stats = BadgeActivityStats(
        xp_gained=100,
        missions_completed=2,
        tracks_created=3,
        tracks_completed=4,
        lessons_completed=5,
        right_answers=6,
        day_streak=7,
    )

    assert BadgeProgressService._criteria_value(
        BadgeCriteriaEnum(criteria), stats
    ) == getattr(stats, attribute)


@pytest.mark.parametrize(
    "previous,last_active,today,expected",
    [
        (0, date(2026, 10, 21), date(2026, 10, 22), 1),
        (3, date(2026, 10, 21), date(2026, 10, 22), 4),
        (3, date(2026, 10, 22), date(2026, 10, 22), 3),
        (3, date(2026, 10, 20), date(2026, 10, 22), 1),
        (3, date(2026, 10, 23), date(2026, 10, 22), 3),
    ],
)
def test_daily_streak_advances_once_per_utc_day(
    previous, last_active, today, expected
):
    assert (
        BadgeProgressService._next_streak(previous, last_active, today)
        == expected
    )
