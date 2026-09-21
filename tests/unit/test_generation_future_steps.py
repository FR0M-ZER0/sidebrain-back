import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.generation_schema import GeneratedTrack


def test_future_steps_reject_detailed_content():
    with pytest.raises(ValidationError):
        GeneratedTrack(
            title="Python",
            description="Fundamentos",
            steps=[
                {"position": 1, "level": "beginner", "title": "Base"},
                {
                    "position": 2,
                    "level": "intermediate",
                    "title": "Prática",
                    "mission": {
                        "title": "Missão",
                        "difficulty": "easy",
                        "xp_reward": 10,
                        "criteria": "complete_a_step",
                        "criteria_value": 1,
                    },
                },
            ],
        )
