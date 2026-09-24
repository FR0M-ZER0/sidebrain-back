from uuid import uuid4

import pytest

from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentAnswersRequest,
    AssessmentContext,
    AssessmentCreateRequest,
    AssessmentDetail,
    GeneratedAssessmentPayload,
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


def test_create_request_normalizes_and_forbids_extra_fields():
    request = AssessmentCreateRequest.model_validate(
        {
            "subject": "  Python assíncrono  ",
            "objective": "  Criar APIs  ",
            "skip": False,
        }
    )

    assert request.subject == "Python assíncrono"
    assert request.objective == "Criar APIs"
    with pytest.raises(ValueError):
        AssessmentCreateRequest.model_validate(
            {"subject": "Python", "skip": False, "user_id": "forbidden"}
        )


def test_create_request_requires_subject_even_when_skipping():
    with pytest.raises(ValueError):
        AssessmentCreateRequest(subject="   ", skip=True)


def test_skip_allows_absent_objective_but_rejects_blank_objective():
    request = AssessmentCreateRequest(subject="  Álgebra  ", skip=True)
    assert request.subject == "Álgebra"
    assert request.objective is None

    with pytest.raises(ValueError):
        AssessmentCreateRequest(
            subject="Álgebra",
            objective="   ",
            skip=True,
        )


def test_generated_payload_requires_distinct_questions_and_valid_answer_key():
    payload = {
        "questions": [
            {
                **VALID_QUESTION,
                "id": f"q{index}",
                "correct_alternative_id": "a",
            }
            for index in range(1, 6)
        ]
    }

    generated = GeneratedAssessmentPayload.model_validate(payload)
    assert len(generated.questions) == 5

    payload["questions"][0]["correct_alternative_id"] = "unknown"
    with pytest.raises(ValueError):
        GeneratedAssessmentPayload.model_validate(payload)


def test_answers_request_requires_five_distinct_questions_and_forbids_extra():
    answers = [
        {"question_id": question_id, "alternative_id": uuid4()}
        for question_id in [uuid4() for _ in range(5)]
    ]
    request = AssessmentAnswersRequest(answers=answers)
    assert len(request.answers) == 5

    with pytest.raises(ValueError):
        AssessmentAnswersRequest(answers=answers[:4])
    with pytest.raises(ValueError):
        AssessmentAnswersRequest(answers=[*answers[:4], answers[0]])
    with pytest.raises(ValueError):
        AssessmentAnswersRequest.model_validate(
            {"answers": answers, "score": 5}
        )


@pytest.mark.parametrize(
    "reserved",
    ["user_id", "score", "level", "status", "is_correct"],
)
def test_answer_item_rejects_server_controlled_fields(reserved):
    answers = [
        {
            "question_id": str(uuid4()),
            "alternative_id": str(uuid4()),
        }
        for _ in range(5)
    ]
    answers[0][reserved] = True

    with pytest.raises(ValueError):
        AssessmentAnswersRequest.model_validate({"answers": answers})


@pytest.mark.parametrize("field", ["question_id", "alternative_id"])
def test_answer_item_requires_valid_uuids(field):
    answers = [
        {
            "question_id": str(uuid4()),
            "alternative_id": str(uuid4()),
        }
        for _ in range(5)
    ]
    answers[0][field] = "not-a-uuid"

    with pytest.raises(ValueError):
        AssessmentAnswersRequest.model_validate({"answers": answers})


def test_public_detail_uses_business_names_and_enforces_state_invariants():
    payload = {
        "assessment_id": str(uuid4()),
        "subject": "Python",
        "objective": None,
        "skip": False,
        "status": "pending",
        "questions": [],
        "score": None,
        "level": None,
        "error_code": None,
        "created_at": "2026-09-24T12:00:00",
        "updated_at": "2026-09-24T12:00:00",
        "completed_at": None,
    }

    detail = AssessmentDetail.model_validate(payload)
    assert set(detail.model_dump(mode="json")) == set(payload)

    payload["score"] = 1
    with pytest.raises(ValueError):
        AssessmentDetail.model_validate(payload)
