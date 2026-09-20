import pytest

from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentContext,
    KnowledgeAssessmentResult,
)

VALID_QUESTION = {
    "id": "q1",
    "statement": "Qual afirmação descreve melhor o uso de asyncio?",
    "alternatives": [
        {
            "id": "a",
            "text": "Executa operações em paralelo sem bloquear o loop.",
        },
        {"id": "b", "text": "Substitui completamente threads."},
        {"id": "c", "text": "Desativa a execução assíncrona."},
        {"id": "d", "text": "Garante que tudo será síncrono."},
    ],
}


def _generated_payload() -> dict:
    return {
        "assessment_id": "a0c2e6f1-71f8-4f80-91db-123456789abc",
        "status": "generated",
        "level": None,
        "questions": [
            {**VALID_QUESTION, "id": "q1"},
            {**VALID_QUESTION, "id": "q2"},
            {**VALID_QUESTION, "id": "q3"},
            {**VALID_QUESTION, "id": "q4"},
            {**VALID_QUESTION, "id": "q5"},
        ],
    }


def test_generated_result_has_exactly_five_questions():
    result = KnowledgeAssessmentResult.model_validate(_generated_payload())

    assert result.status == "generated"
    assert result.level is None
    assert len(result.questions) == 5
    assert result.questions[0].alternatives[0].text


def test_skipped_result_has_beginner_level_and_no_questions():
    result = KnowledgeAssessmentResult.model_validate(
        {
            "assessment_id": "a0c2e6f1-71f8-4f80-91db-123456789abc",
            "status": "skipped",
            "level": "beginner",
            "questions": [],
        }
    )

    assert result.status == "skipped"
    assert result.level == "beginner"
    assert result.questions == []


def test_assessment_context_requires_subject_when_not_skipping():
    with pytest.raises(ValueError):
        AssessmentContext.model_validate(
            {
                "user_id": "8d4e1d4b-3b0e-4f2d-a5f4-123456789abc",
                "subject": "   ",
                "objective": "Aprender FastAPI",
                "skip": False,
            }
        )
