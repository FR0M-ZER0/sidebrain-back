import json
from types import SimpleNamespace

import pytest

from sidebrain_back.services.rag_routing_service import RagRoutingService


class FakeCompletions:
    def __init__(self, content: str | Exception):
        self.content = content
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.content, Exception):
            raise self.content
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=self.content))
            ]
        )


def _router(
    response: str | Exception,
) -> tuple[RagRoutingService, FakeCompletions]:
    completions = FakeCompletions(response)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return RagRoutingService(client=client), completions


@pytest.mark.parametrize(
    ("goal", "topic", "language"),
    [
        ("Aprender programação em Python", "Python", "python"),
        ("Learn async programming", "JavaScript", "javascript"),
    ],
)
def test_router_accepts_valid_high_confidence_language(
    goal: str, topic: str, language: str
):
    router, completions = _router(
        json.dumps({"use_rag": True, "language": language, "confidence": 0.93})
    )

    decision = router.should_use_rag(goal, topic)

    assert decision.use_rag is True
    assert decision.language == language
    assert decision.confidence == 0.93
    assert len(completions.calls) == 1
    assert completions.calls[0]["response_format"] == {"type": "json_object"}


def test_router_rejects_classifier_confidence_below_threshold():
    router, _ = _router(
        json.dumps({"use_rag": True, "language": "python", "confidence": 0.79})
    )

    decision = router.should_use_rag("Aprender Python", "Python")

    assert decision.use_rag is False
    assert decision.language is None
    assert decision.confidence == 0.79


def test_router_does_not_accept_incidental_language_mention():
    router, _ = _router(
        json.dumps({"use_rag": False, "language": None, "confidence": 0.99})
    )

    decision = router.should_use_rag(
        "Aprender inglês para viajar e visitar um museu de Python",
        "Inglês para viagens",
    )

    assert decision.use_rag is False
    assert decision.language is None


def test_router_uses_strong_deterministic_fallback_when_openai_fails():
    router, _ = _router(RuntimeError("provider unavailable"))

    decision = router.should_use_rag(
        "Quero aprender programação em Python", "Python"
    )

    assert decision.use_rag is True
    assert decision.language == "python"
    assert decision.confidence == 0.80


def test_router_fallback_rejects_weak_or_ambiguous_context():
    router, _ = _router(ValueError("invalid response"))

    decision = router.should_use_rag(
        "Aprender inglês para viajar com alguém que usa Python",
        "Inglês",
    )

    assert decision.use_rag is False
    assert decision.language is None


def test_router_fallback_handles_invalid_json_with_strong_learning_context():
    router, _ = _router("not-json")

    decision = router.should_use_rag(
        "Aprender programação em Python", "Python"
    )

    assert decision.use_rag is True
    assert decision.language == "python"
    assert decision.confidence == 0.80


def test_router_rejects_ambiguous_language_when_unresolved():
    router, _ = _router(
        json.dumps({"use_rag": False, "language": None, "confidence": 0.2})
    )

    decision = router.should_use_rag(
        "Comparar programação em Python e JavaScript",
        "Python e JavaScript",
    )

    assert decision.use_rag is False
    assert decision.language is None
