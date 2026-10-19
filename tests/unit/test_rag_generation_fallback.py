import asyncio
import json
from types import SimpleNamespace

from sidebrain_back.services.rag_generation_context_service import (
    RagGenerationContextService,
)
from sidebrain_back.services.rag_routing_service import RagRoutingService


class FakeCompletions:
    def __init__(self, content):
        self.content = content
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        if isinstance(self.content, Exception):
            raise self.content
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=self.content))
            ]
        )


class FakeRetriever:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = 0

    async def retrieve(self, **_kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return []


def test_unrelated_goal_does_not_call_classifier_embeddings_or_retrieval():
    completions = FakeCompletions("unused")
    router = RagRoutingService(
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions))
    )
    retriever = FakeRetriever()
    context_service = RagGenerationContextService(router, retriever)

    result = asyncio.run(
        context_service.get_references(
            goal="Aprender inglês para viagens", topic="Inglês"
        )
    )

    assert result == []
    assert completions.calls == 0
    assert retriever.calls == 0


def test_incidental_mention_and_retrieval_failure_fail_open():
    completions = FakeCompletions(
        json.dumps({"use_rag": False, "language": None, "confidence": 0.98})
    )
    router = RagRoutingService(
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions))
    )
    retriever = FakeRetriever(error=RuntimeError("offline"))
    context_service = RagGenerationContextService(router, retriever)

    result = asyncio.run(
        context_service.get_references(
            goal="Aprender inglês para viagens; visitar o museu Python",
            topic="Inglês",
        )
    )

    assert result == []
    assert retriever.calls == 0


def test_classifier_failure_never_blocks_content_generation_context():
    completions = FakeCompletions(RuntimeError("Groq unavailable"))
    router = RagRoutingService(
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions))
    )
    retriever = FakeRetriever()
    context_service = RagGenerationContextService(router, retriever)

    result = asyncio.run(
        context_service.get_references(
            goal="Aprender inglês com uma menção a Python",
            topic="Inglês",
        )
    )

    assert result == []
    assert retriever.calls == 0


def test_retrieval_failure_fails_open_for_a_classified_programming_goal():
    completions = FakeCompletions(
        json.dumps({"use_rag": True, "language": "python", "confidence": 0.95})
    )
    router = RagRoutingService(
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions))
    )
    retriever = FakeRetriever(error=RuntimeError("database unavailable"))
    context_service = RagGenerationContextService(router, retriever)

    result = asyncio.run(
        context_service.get_references(
            goal="Learn Python programming", topic="Python"
        )
    )

    assert result == []
    assert retriever.calls == 1
