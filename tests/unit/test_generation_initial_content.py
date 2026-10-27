import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.generation_schema import GeneratedLesson


def test_initial_lesson_requires_five_quizzes_and_positive_position():
    with pytest.raises(ValidationError):
        GeneratedLesson(position=0, title="Lição", text="Texto")

    lesson = GeneratedLesson(
        position=1,
        title="Lição",
        text="## Conceito\n\n" + "Texto. " * 150,
        quizzes=[
            {"question": f"**Pergunta {index}:** explique?"}
            for index in range(1, 6)
        ],
    )

    assert len(lesson.quizzes) == 5
