from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.schemas.step_schema import (
    StepCreate,
    StepResponse,
    StepUpdate,
)


def test_step_input_normalizes_title_and_rejects_unknown_fields():
    payload = StepCreate(level="beginner", title="  Intro  ")

    assert payload.level == StepLevelEnum.BEGINNER
    assert payload.title == "Intro"

    with pytest.raises(ValidationError):
        StepCreate(level="beginner", title="Intro", status="done")


def test_step_input_requires_valid_level_and_non_empty_title():
    with pytest.raises(ValidationError):
        StepCreate(level="expert", title="Intro")
    with pytest.raises(ValidationError):
        StepCreate(level="beginner", title="   ")
    with pytest.raises(ValidationError):
        StepUpdate(level="beginner", title="x" * 256)


def test_step_response_hides_physical_and_internal_fields():
    response = StepResponse.model_validate(
        {
            "stp_id": uuid4(),
            "stp_level": "beginner",
            "stp_title": "Intro",
            "stp_status": "idle",
            "stp_updated_at": datetime.now(),
            "stp_track_id": uuid4(),
            "stp_is_deleted": False,
            "lessons": [],
            "missions": [],
        }
    )

    assert set(response.model_dump()) == {
        "id",
        "level",
        "title",
        "status",
        "updated_at",
        "lessons",
        "missions",
    }
