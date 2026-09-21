import pytest
from pydantic import ValidationError

from sidebrain_back.schemas.generation_schema import GeneratedLesson


def test_initial_lesson_requires_one_quiz_and_positive_position():
    with pytest.raises(ValidationError):
        GeneratedLesson(position=0, title="Lição", text="Texto")

    lesson = GeneratedLesson(
        position=1,
        title="Lição",
        text="Texto",
        quiz={"question": "Pergunta"},
    )

    assert lesson.quiz.question == "Pergunta"