import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.generation_schema import GeneratedTrack


def _step(position: int, **extra):
    return {
        "position": position,
        "level": "beginner" if position == 1 else "intermediate",
        "title": f"Etapa {position}",
        "lessons": [],
        "mission": None,
        **extra,
    }


def test_generated_track_requires_contiguous_positions_and_future_structure():
    with pytest.raises(ValidationError):
        GeneratedTrack(
            title="Trilha",
            description="Descrição",
            steps=[_step(1), _step(3)],
        )

    with pytest.raises(ValidationError):
        GeneratedTrack(
            title="Trilha",
            description="Descrição",
            steps=[
                _step(
                    1,
                ),
                _step(
                    2,
                    lessons=[
                        {
                            "position": 1,
                            "title": "Lição",
                            "text": "Texto",
                            "quiz": {"question": "Pergunta"},
                        }
                    ],
                ),
            ],
        )


def test_generated_track_accepts_first_step_content_and_optional_mission():
    generated = GeneratedTrack(
        title="Trilha",
        description="Descrição",
        steps=[
            _step(
                1,
                lessons=[
                    {
                        "position": 1,
                        "title": "Variáveis",
                        "text": "Conteúdo",
                        "quiz": {"question": "O que é uma variável?"},
                    }
                ],
                mission={
                    "title": "Pratique",
                    "difficulty": "easy",
                    "xp_reward": 10,
                    "criteria": "number_of_lessons_completed",
                    "criteria_value": 1,
                },
            ),
            _step(2),
        ],
    )

    assert len(generated.steps[0].lessons) == 1
    assert generated.steps[1].lessons == []