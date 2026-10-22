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


def _initial_step(**overrides):
    step = _step(
        1,
        lessons=[
            {
                "position": position,
                "title": f"Lição {position}",
                "text": "Conteúdo",
                "quiz": {"question": f"Pergunta {position}?"},
            }
            for position in range(1, 4)
        ],
        mission={
            "title": "Pratique",
            "difficulty": "easy",
            "xp_reward": 10,
            "criteria": "number_of_lessons_completed",
            "criteria_value": 1,
        },
    )
    step.update(overrides)
    return step


def test_generated_track_requires_contiguous_positions_and_future_structure():
    with pytest.raises(ValidationError):
        GeneratedTrack(
            icon="📘",
            title="Trilha",
            description="Descrição",
            steps=[_initial_step(), _step(3)],
        )

    with pytest.raises(ValidationError):
        GeneratedTrack(
            icon="📘",
            title="Trilha",
            description="Descrição",
            steps=[
                _initial_step(),
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


def test_generated_track_requires_first_step_content_and_mission():
    generated = GeneratedTrack(
        icon="📘",
        title="Trilha",
        description="Descrição",
        steps=[
            _initial_step(),
            _step(2),
        ],
    )

    assert len(generated.steps[0].lessons) == 3
    assert generated.steps[0].mission.title == "Pratique"
    assert generated.steps[1].lessons == []


def test_generated_track_rejects_first_step_without_mission_or_three_lessons():
    with pytest.raises(ValidationError):
        GeneratedTrack(
            icon="📘",
            title="Trilha",
            description="Descrição",
            steps=[_initial_step(mission=None)],
        )

    with pytest.raises(ValidationError):
        GeneratedTrack(
            icon="📘",
            title="Trilha",
            description="Descrição",
            steps=[_initial_step(lessons=_initial_step()["lessons"][:2])],
        )
