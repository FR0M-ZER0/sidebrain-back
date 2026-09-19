import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentContext,
)
from sidebrain_back.services.knowledge_assessment_generator import (
    KnowledgeAssessmentGenerator,
)
from sidebrain_back.services.knowledge_assessment_service import (
    KnowledgeAssessmentService,
)


class FakeCompletions:
    def __init__(self, *, content: str | None = None, error=None):
        self.content = content
        self.error = error

    def create(self, **_kwargs):
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content),
                )
            ]
        )


def make_generator(*, content: str | None = None, error=None):
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=FakeCompletions(content=content, error=error)
        )
    )
    return KnowledgeAssessmentGenerator(client)


def test_provider_exception_is_not_replaced_by_synthetic_assessment():
    generator = make_generator(error=RuntimeError("invalid credential"))

    with pytest.raises(RuntimeError, match="invalid credential"):
        generator.generate("Python")


@pytest.mark.parametrize("content", [None, "", "not-json"])
def test_empty_or_invalid_provider_content_fails(content):
    generator = make_generator(content=content)

    with pytest.raises((ValueError, json.JSONDecodeError)):
        generator.generate("Python")


def test_incomplete_provider_payload_is_rejected_without_fallback():
    generator = make_generator(
        content=json.dumps(
            {
                "assessment_id": str(uuid4()),
                "status": "generated",
                "level": None,
            }
        )
    )
    service = KnowledgeAssessmentService(generator)

    with pytest.raises(ValueError):
        service.prepare_assessment(
            AssessmentContext(
                user_id=str(uuid4()),
                subject="Python",
                skip=False,
            )
        )
