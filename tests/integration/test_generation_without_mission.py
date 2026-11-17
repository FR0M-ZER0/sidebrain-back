import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.generation_schema import GeneratedTrack


def test_first_step_generation_rejects_missing_mission_and_lessons():
    with pytest.raises(ValidationError):
        GeneratedTrack(
            icon="📘",
            title="Python",
            description="Fundamentos",
            steps=[{"position": 1, "level": "beginner", "title": "Base"}],
        )
