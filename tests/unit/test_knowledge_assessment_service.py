from uuid import uuid4

import pytest

from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentContext,
    KnowledgeAssessmentResult,
)
from sidebrain_back.services.knowledge_assessment_service import (
    KnowledgeAssessmentService,
)


def _question(number: str) -> dict:
    return {
        "id": f"q{number}",
        "statement": f"Pergunta {number} sobre o assunto.",
        "alternatives": [
            {"id": "a", "text": "Alternativa A"},
            {"id": "b", "text": "Alternativa B"},
            {"id": "c", "text": "Alternativa C"},
            {"id": "d", "text": "Alternativa D"},
        ],
    }


def _valid_generated_result() -> dict:
    return {
        "assessment_id": str(uuid4()),
        "status": "generated",
        "level": None,
        "questions": [_question(str(index)) for index in range(1, 6)],
    }


class FakeGenerator:
    def __init__(self, payload: dict | None = None):
        self.payload = payload or _valid_generated_result()
        self.calls: list[tuple[str | None, str | None]] = []

    def generate(self, subject: str, objective: str | None = None) -> dict:
        self.calls.append((subject, objective))
        return self.payload


def test_service_generates_assessment_for_valid_subject():
    generator = FakeGenerator()
    service = KnowledgeAssessmentService(generator)

    result = service.prepare_assessment(
        AssessmentContext(
            user_id=str(uuid4()),
            subject="Python assíncrono",
            objective="Criar APIs com FastAPI",
            skip=False,
        )
    )

    assert isinstance(result, KnowledgeAssessmentResult)
    assert result.status == "generated"
    assert len(result.questions) == 5
    assert generator.calls == [("Python assíncrono", "Criar APIs com FastAPI")]


def test_service_rejects_blank_subject_when_not_skipping():
    service = KnowledgeAssessmentService(FakeGenerator())

    with pytest.raises(ValueError):
        service.prepare_assessment(
            AssessmentContext(
                user_id=str(uuid4()),
                subject="   ",
                objective="Objetivo opcional",
                skip=False,
            )
        )


def test_service_returns_skip_result_without_calling_provider():
    generator = FakeGenerator()
    service = KnowledgeAssessmentService(generator)

    result = service.prepare_assessment(
        AssessmentContext(
            user_id=str(uuid4()),
            subject="Ignorado",
            objective="Ignorado",
            skip=True,
        )
    )

    assert result.status == "skipped"
    assert result.level == "beginner"
    assert result.questions == []
    assert generator.calls == []
