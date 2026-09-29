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
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
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


def _provider_payload() -> dict:
    return {
        "questions": [
            {
                "id": f"q{question}",
                "statement": f"Pergunta {question}",
                "alternatives": [
                    {
                        "id": f"q{question}a{alternative}",
                        "text": f"A{alternative}",
                    }
                    for alternative in range(1, 5)
                ],
                "correct_alternative_id": f"q{question}a1",
            }
            for question in range(1, 6)
        ]
    }


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


def test_v2_prompt_delegates_only_questions_and_private_answer_key():
    generator = make_generator(content=json.dumps(_provider_payload()))

    payload = generator.generate("Python", "FastAPI")

    assert payload.model_dump(mode="json") == _provider_payload()
    request = generator.client.chat.completions
    prompt = request.last_kwargs["messages"][1]["content"]
    assert "correct_alternative_id" in prompt
    assert "assessment_id" not in prompt
    assert "'status'" not in prompt
    assert "'level'" not in prompt


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload["questions"].pop(),
        lambda payload: payload["questions"].__setitem__(
            1, payload["questions"][0]
        ),
        lambda payload: payload["questions"][0]["alternatives"].pop(),
        lambda payload: payload["questions"][0].__setitem__(
            "correct_alternative_id", "foreign"
        ),
        lambda payload: payload.__setitem__("status", "generated"),
    ],
)
def test_generator_rejects_incomplete_duplicate_or_provider_owned_fields(
    mutate,
):
    payload = _provider_payload()
    mutate(payload)
    generator = make_generator(content=json.dumps(payload))

    with pytest.raises(ValueError):
        generator.generate("Python")
