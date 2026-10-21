import asyncio
import importlib
from types import SimpleNamespace
from uuid import uuid4

from sidebrain_back.schemas.generation_schema import GenerationInput
from sidebrain_back.schemas.rag_schema import RagReferenceSchema
from sidebrain_back.services.generation_service import GenerationService

generation_task_module = importlib.import_module(
    "sidebrain_back.tasks.generate_track_task"
)


def _reference() -> RagReferenceSchema:
    return RagReferenceSchema(
        chunk_id="a" * 64,
        text="asyncio.run() executes a coroutine.",
        source_name="python-library",
        source_url="https://docs.python.org/3/library/asyncio.html",
        title="asyncio",
        section_path="asyncio > Runners",
        language="python",
        level="intermediate",
        content_type="reference",
        topics=["asyncio", "coroutines"],
        license="PSF-2.0",
        license_url="https://docs.python.org/3/license.html",
        external_processing_allowed=True,
    )


def test_initial_generation_prompt_adds_cited_untrusted_reference_block():
    payload = GenerationInput(
        request_id=uuid4(),
        user_id=uuid4(),
        goal="Aprender programação assíncrona em Python",
        topic="asyncio",
    )

    prompt = GenerationService.build_prompt(
        payload,
        reference_context=[_reference()],
    )

    assert "material de referência não confiável" in prompt.lower()
    assert "https://docs.python.org/3/library/asyncio.html" in prompt
    assert "asyncio > Runners" in prompt
    assert "asyncio.run() executes a coroutine." in prompt
    assert "um único objeto JSON" in prompt
    assert "somente para a etapa de posição 1" in prompt


def test_initial_prompt_without_references_keeps_existing_prompt_unchanged():
    payload = GenerationInput(
        request_id=uuid4(),
        user_id=uuid4(),
        goal="Aprender inglês para viagens",
        topic="Inglês",
    )

    prompt_without_reference = GenerationService.build_prompt(payload)
    prompt_with_empty_reference = GenerationService.build_prompt(
        payload, reference_context=[]
    )
    assert prompt_without_reference == prompt_with_empty_reference


def test_generation_task_passes_rag_context_without_changing_task_output(
    monkeypatch,
):
    payload = GenerationInput(
        request_id=uuid4(),
        user_id=uuid4(),
        goal="Aprender programação em Python",
        topic="Python",
    )
    reference = _reference()
    service_calls = []
    context_calls = []

    class SessionContext:
        async def __aenter__(self):
            return SimpleNamespace(in_transaction=lambda: False)

        async def __aexit__(self, *_args):
            return None

    class Repository:
        async def get_by_request_id(self, _request_id):
            return None

    class Service:
        def __init__(self, *_args):
            pass

        async def generate(self, received_payload, reference_context=None):
            service_calls.append((received_payload, reference_context))
            return SimpleNamespace(
                model_dump=lambda **_kwargs: {"status": "succeeded"}
            )

    class ContextService:
        async def get_references(self, **kwargs):
            context_calls.append(kwargs)
            return [reference]

    monkeypatch.setattr(
        generation_task_module, "async_session", SessionContext
    )
    monkeypatch.setattr(
        generation_task_module,
        "GenerationRepository",
        lambda _db: Repository(),
    )
    monkeypatch.setattr(generation_task_module, "GenerationService", Service)

    result = asyncio.run(
        generation_task_module._run_generation(
            payload, rag_context_service=ContextService()
        )
    )

    assert result == {"status": "succeeded"}
    assert context_calls == [
        {"goal": payload.goal, "topic": payload.topic, "level": None}
    ]
    assert service_calls == [(payload, [reference])]


def test_generation_task_skips_rag_lookup_when_request_already_has_track(
    monkeypatch,
):
    payload = GenerationInput(
        request_id=uuid4(),
        user_id=uuid4(),
        goal="Aprender programação em Python",
        topic="Python",
    )
    context_calls = []
    service_calls = []

    class SessionContext:
        async def __aenter__(self):
            return SimpleNamespace(in_transaction=lambda: False)

        async def __aexit__(self, *_args):
            return None

    class Repository:
        async def get_by_request_id(self, _request_id):
            return object()

    class Service:
        def __init__(self, *_args):
            pass

        async def generate(self, received_payload, reference_context=None):
            service_calls.append((received_payload, reference_context))
            return SimpleNamespace(
                model_dump=lambda **_kwargs: {"status": "succeeded"}
            )

    class ContextService:
        async def get_references(self, **kwargs):
            context_calls.append(kwargs)
            return []

    monkeypatch.setattr(
        generation_task_module, "async_session", SessionContext
    )
    monkeypatch.setattr(
        generation_task_module,
        "GenerationRepository",
        lambda _db: Repository(),
    )
    monkeypatch.setattr(generation_task_module, "GenerationService", Service)

    asyncio.run(
        generation_task_module._run_generation(
            payload, rag_context_service=ContextService()
        )
    )

    assert context_calls == []
    assert service_calls == [(payload, None)]
