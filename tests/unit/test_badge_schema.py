import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.badge_schema import BadgeCreate, BadgeUpdate


def test_badge_create_strips_name_and_accepts_public_enums():
    badge = BadgeCreate(
        name="  Primeira trilha  ",
        description="Conclua uma trilha.",
        rarity="common",
        criteria="tracks_completed",
        criteria_value=1,
    )

    assert badge.name == "Primeira trilha"
    assert badge.rarity.value == "common"
    assert badge.criteria.value == "tracks_completed"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "name": "   ",
            "rarity": "common",
            "criteria": "xp_gained",
            "criteria_value": 1,
        },
        {
            "name": "x" * 256,
            "rarity": "common",
            "criteria": "xp_gained",
            "criteria_value": 1,
        },
        {
            "name": "x",
            "rarity": "unknown",
            "criteria": "xp_gained",
            "criteria_value": 1,
        },
        {
            "name": "x",
            "rarity": "common",
            "criteria": "unknown",
            "criteria_value": 1,
        },
        {
            "name": "x",
            "rarity": "common",
            "criteria": "xp_gained",
            "criteria_value": 0,
        },
    ],
)
def test_badge_create_rejects_invalid_fields(payload):
    with pytest.raises(ValidationError):
        BadgeCreate.model_validate(payload)


def test_badge_update_requires_a_field_and_rejects_internal_fields():
    with pytest.raises(ValidationError):
        BadgeUpdate.model_validate({})
    with pytest.raises(ValidationError):
        BadgeUpdate.model_validate({"name": None})
    with pytest.raises(ValidationError):
        BadgeUpdate.model_validate({"bdg_is_deleted": True})


def test_badge_update_preserves_explicit_null_description():
    update = BadgeUpdate(description=None)

    assert update.model_dump(exclude_unset=True) == {"description": None}
