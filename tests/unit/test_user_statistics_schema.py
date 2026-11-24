import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.user_statistics_schema import (
    UserStatisticsResponse,
)


def test_user_statistics_response_uses_public_camel_case_contract():
    response = UserStatisticsResponse(
        xp=1250,
        missions_completed=12,
        position=3,
        badges_unlocked=4,
        current_day_streak=7,
    )

    assert response.model_dump(by_alias=True) == {
        "xp": 1250,
        "missionsCompleted": 12,
        "position": 3,
        "badgesUnlocked": 4,
        "currentDayStreak": 7,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("xp", -1),
        ("missions_completed", -1),
        ("position", 0),
        ("badges_unlocked", -1),
        ("current_day_streak", -1),
    ],
)
def test_user_statistics_response_rejects_values_below_contract_minimum(
    field, value
):
    data = {
        "xp": 0,
        "missions_completed": 0,
        "position": 1,
        "badges_unlocked": 0,
        "current_day_streak": 0,
    }
    data[field] = value

    with pytest.raises(ValidationError):
        UserStatisticsResponse(**data)
