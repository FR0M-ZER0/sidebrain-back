from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.schemas.quiz_schema import (
    AnswerResponse,
    QuizCreateRequest,
    QuizResponse,
    QuizUpdateRequest,
)


@pytest.mark.parametrize("schema", [QuizCreateRequest, QuizUpdateRequest])
def test_question_is_trimmed_before_length_validation(schema):
    payload = schema(question=f"  {'x' * 1000}  ")

    assert payload.question == "x" * 1000


@pytest.mark.parametrize("schema", [QuizCreateRequest, QuizUpdateRequest])
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": "   "},
        {"question": "x" * 1001},
        {"question": "valid", "lesson_id": str(uuid4())},
        {"question": "valid", "answers": []},
        {"question": "valid", "qui_is_deleted": False},
    ],
)
def test_question_payload_rejects_invalid_or_internal_fields(schema, payload):
    with pytest.raises(ValueError):
        schema.model_validate(payload)


def test_quiz_response_uses_public_aliases_and_empty_answers():
    quiz = SimpleNamespace(
        qui_id=uuid4(),
        qui_lesson_id=uuid4(),
        qui_question="What is a variable?",
        answers=[],
    )

    response = QuizResponse.model_validate(quiz)

    assert response.model_dump() == {
        "id": quiz.qui_id,
        "lesson_id": quiz.qui_lesson_id,
        "question": quiz.qui_question,
        "answers": [],
    }


def test_answer_response_uses_public_fields_and_typed_rate():
    answer = SimpleNamespace(
        ans_id=uuid4(),
        ans_user_id=uuid4(),
        ans_text="A named reference to a value",
        ans_rate=AnswerRateEnum.PERFECT,
    )

    response = AnswerResponse.model_validate(answer)

    assert response.rate is AnswerRateEnum.PERFECT
    assert response.model_dump() == {
        "id": answer.ans_id,
        "user_id": answer.ans_user_id,
        "text": answer.ans_text,
        "rate": AnswerRateEnum.PERFECT,
    }


def test_answer_response_rejects_unknown_rate():
    with pytest.raises(ValueError):
        AnswerResponse.model_validate(
            {
                "ans_id": uuid4(),
                "ans_user_id": uuid4(),
                "ans_text": "Invalid",
                "ans_rate": "invalid",
            }
        )
