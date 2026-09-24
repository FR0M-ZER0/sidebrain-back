from uuid import uuid4

from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentAnswersRequest,
    AssessmentDetail,
    KnowledgeAssessmentResult,
)


def test_generated_contract_has_exactly_five_questions():
    payload = {
        "assessment_id": str(uuid4()),
        "status": "generated",
        "level": None,
        "questions": [
            {
                "id": "q1",
                "statement": "Pergunta 1.",
                "alternatives": [
                    {"id": "a", "text": "A"},
                    {"id": "b", "text": "B"},
                    {"id": "c", "text": "C"},
                    {"id": "d", "text": "D"},
                ],
            }
            for _ in range(5)
        ],
    }

    result = KnowledgeAssessmentResult.model_validate(payload)

    assert result.model_dump(mode="json")["status"] == "generated"
    assert len(result.model_dump(mode="json")["questions"]) == 5


def test_skipped_contract_has_initial_level_and_empty_questions():
    payload = {
        "assessment_id": str(uuid4()),
        "status": "skipped",
        "level": "beginner",
        "questions": [],
    }

    result = KnowledgeAssessmentResult.model_validate(payload)

    assert result.status == "skipped"
    assert result.level == "beginner"
    assert result.questions == []


def test_public_assessment_contract_never_exposes_storage_or_answer_key():
    detail = AssessmentDetail.model_validate(
        {
            "assessment_id": str(uuid4()),
            "subject": "Python",
            "objective": None,
            "skip": False,
            "status": "generated",
            "questions": [
                {
                    "id": str(uuid4()),
                    "statement": f"Question {index}",
                    "alternatives": [
                        {"id": str(uuid4()), "text": f"Alternative {item}"}
                        for item in range(4)
                    ],
                }
                for index in range(5)
            ],
            "score": None,
            "level": None,
            "error_code": None,
            "created_at": "2026-09-24T12:00:00",
            "updated_at": "2026-09-24T12:00:00",
            "completed_at": None,
        }
    )

    serialized = str(detail.model_dump(mode="json"))
    assert "is_correct" not in serialized
    assert "correct_alternative_id" not in serialized
    assert "kas_" not in serialized
    assert "kaq_" not in serialized
    assert "kaa_" not in serialized


def test_answer_contract_contains_only_public_selection_ids():
    request = AssessmentAnswersRequest.model_validate(
        {
            "answers": [
                {
                    "question_id": str(uuid4()),
                    "alternative_id": str(uuid4()),
                }
                for _ in range(5)
            ]
        }
    )

    serialized = request.model_dump(mode="json")
    assert set(serialized) == {"answers"}
    assert all(
        set(answer) == {"question_id", "alternative_id"}
        for answer in serialized["answers"]
    )
