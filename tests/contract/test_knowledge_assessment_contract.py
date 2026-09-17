from uuid import uuid4

from sidebrain_back.schemas.knowledge_assessment_schema import (
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
