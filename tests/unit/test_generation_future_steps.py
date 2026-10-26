import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.generation_schema import GeneratedTrack


def test_future_steps_reject_detailed_content():
    with pytest.raises(ValidationError):
        GeneratedTrack(
            icon="📘",
            title="Python",
            description="Fundamentos",
            steps=[
                {
                    "position": 1,
                    "level": "beginner",
                    "title": "Base",
                    "lessons": [
                        {
                            "position": position,
                            "title": f"Lição {position}",
                            "text": "## Conceito\n\n" + "Conteúdo. " * 120,
                            "quizzes": [
                                {
                                    "question": (
                                        f"**Pergunta {index}:** explique?"
                                    )
                                }
                                for index in range(1, 6)
                            ],
                        }
                        for position in range(1, 4)
                    ],
                    "missions": [
                        {
                            "title": "Pratique",
                            "difficulty": "easy",
                            "xp_reward": 10,
                            "criteria": "complete_a_step",
                            "criteria_value": 1,
                        }
                    ]
                    * 3,
                },
                {
                    "position": 2,
                    "level": "intermediate",
                    "title": "Prática",
                    "lessons": [
                        {
                            "position": 1,
                            "title": "Conteúdo futuro",
                            "text": "## Conceito\n\n" + "Conteúdo. " * 120,
                            "quizzes": [
                                {
                                    "question": (
                                        f"**Pergunta {index}:** explique?"
                                    )
                                }
                                for index in range(1, 6)
                            ],
                        }
                    ],
                    "missions": [
                        {
                            "title": "Missão",
                            "difficulty": "easy",
                            "xp_reward": 10,
                            "criteria": "complete_a_step",
                            "criteria_value": 1,
                        }
                    ]
                    * 3,
                },
            ],
        )
