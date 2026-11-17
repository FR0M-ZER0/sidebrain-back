import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.mission_schema import MissionCreate, MissionUpdate


def valid_payload() -> dict:
    return {
        "title": " Complete lessons ",
        "difficulty": "medium",
        "xpReward": 100,
        "criteria": "number_of_lessons_completed",
        "criteriaValue": 3,
    }


def test_mission_create_normalizes_title_and_accepts_camel_case():
    payload = MissionCreate(**valid_payload())

    assert payload.title == "Complete lessons"
    assert payload.xp_reward == 100
    assert payload.criteria_value == 3


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "   "},
        {"title": "x" * 256},
        {"xpReward": -1},
        {"criteriaValue": 0},
        {"difficulty": "invalid"},
    ],
)
def test_mission_create_rejects_invalid_values(changes):
    payload = valid_payload()
    payload.update(changes)

    with pytest.raises(ValidationError):
        MissionCreate(**payload)


def test_mission_update_is_partial_but_not_empty():
    assert MissionUpdate(xpReward=200).xp_reward == 200

    with pytest.raises(ValidationError):
        MissionUpdate()
