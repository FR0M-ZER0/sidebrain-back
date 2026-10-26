import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.generation_schema import (
    GeneratedLesson,
    GeneratedTrack,
)


def _lesson_text(length=1200):
    prefix = "## Conceito\n\n"
    return prefix + ("Conteúdo explicativo. " * 100)[: length - len(prefix)]


def _quizzes():
    return [
        {"question": f"**Pergunta {index}:** explique o conceito?"}
        for index in range(1, 6)
    ]


def _mission():
    return {
        "title": "Pratique",
        "difficulty": "easy",
        "xp_reward": 10,
        "criteria": "number_of_lessons_completed",
        "criteria_value": 1,
    }


def _step(position: int, **extra):
    return {
        "position": position,
        "level": "beginner" if position == 1 else "intermediate",
        "title": f"Etapa {position}",
        "lessons": [],
        "missions": [_mission(), _mission(), _mission()],
        **extra,
    }


def _initial_step(**overrides):
    step = _step(
        1,
        lessons=[
            {
                "position": position,
                "title": f"Lição {position}",
                "text": _lesson_text(),
                "quizzes": _quizzes(),
            }
            for position in range(1, 4)
        ],
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
                            "text": _lesson_text(),
                            "quizzes": _quizzes(),
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
    assert len(generated.steps[0].missions) == 3
    assert generated.steps[1].lessons == []


def test_generated_track_requires_three_missions_and_lessons():
    with pytest.raises(ValidationError):
        GeneratedTrack(
            icon="📘",
            title="Trilha",
            description="Descrição",
            steps=[_initial_step(missions=[])],
        )

    with pytest.raises(ValidationError):
        GeneratedTrack(
            icon="📘",
            title="Trilha",
            description="Descrição",
            steps=[_initial_step(lessons=_initial_step()["lessons"][:2])],
        )

    lessons = _initial_step()["lessons"]
    lessons[0]["quizzes"] = _quizzes()[:4]
    with pytest.raises(ValidationError):
        GeneratedTrack(
            icon="📘",
            title="Trilha",
            description="Descrição",
            steps=[_initial_step(lessons=lessons)],
        )


@pytest.mark.parametrize("length", [999, 2001])
def test_generated_lesson_enforces_text_length_bounds(length):
    with pytest.raises(ValidationError):
        GeneratedLesson(
            position=1,
            title="Lição",
            text=_lesson_text(length),
            quizzes=_quizzes(),
        )


@pytest.mark.parametrize("length", [1000, 2000])
def test_generated_lesson_accepts_text_length_boundaries(length):
    lesson = GeneratedLesson(
        position=1,
        title="Lição",
        text=_lesson_text(length),
        quizzes=_quizzes(),
    )

    assert len(lesson.text) == length
