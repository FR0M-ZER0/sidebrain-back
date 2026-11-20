from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from sidebrain_back.core.constants import Env
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.repositories.knowledge_assessment_repository import (
    KnowledgeAssessmentRepository,
)
from sidebrain_back.schemas.knowledge_assessment_schema import (
    GeneratedAssessmentPayload,
)
from sidebrain_back.services.generation_memory_service import (
    GenerationMemoryService,
)


def assessment_payload():
    return GeneratedAssessmentPayload.model_validate(
        {
            "questions": [
                {
                    "id": str(i),
                    "statement": f"Pergunta {i}",
                    "alternatives": [
                        {"id": str(j), "text": f"Alternativa {j}"}
                        for j in range(4)
                    ],
                    "correct_alternative_id": "0",
                }
                for i in range(5)
            ]
        }
    )


@pytest.mark.anyio
async def test_assessment_cache_hit_does_not_call_provider(monkeypatch):
    monkeypatch.setattr(Env, "AI_MEMORY_ENABLED", True)
    monkeypatch.setattr(Env, "AI_MEMORY_REDIS_LOCK_ENABLED", False)
    monkeypatch.setattr(
        "sidebrain_back.services.generation_memory_service."
        "TopicAliasRepository.get_active_by_alias",
        AsyncMock(return_value=None),
    )
    payload = assessment_payload()
    cache_id = uuid4()
    cache = SimpleNamespace(
        get_ready=AsyncMock(
            return_value=SimpleNamespace(
                id=cache_id, payload=payload.model_dump(mode="json")
            )
        )
    )
    db = SimpleNamespace(rollback=AsyncMock())
    generator = Mock()

    result, source, result_id = await GenerationMemoryService(
        db, cache
    ).generate(
        content_type="assessment",
        context={"subject": "Python", "objective": "Fundamentos"},
        topic_field="subject",
        schema=GeneratedAssessmentPayload,
        generator=generator,
    )

    assert result == payload
    assert source == "cache"
    assert result_id == cache_id
    generator.assert_not_called()


@pytest.mark.anyio
async def test_provider_failure_releases_owned_reservation(monkeypatch):
    monkeypatch.setattr(Env, "AI_MEMORY_ENABLED", True)
    monkeypatch.setattr(Env, "AI_MEMORY_REDIS_LOCK_ENABLED", False)
    monkeypatch.setattr(
        "sidebrain_back.services.generation_memory_service."
        "TopicAliasRepository.get_active_by_alias",
        AsyncMock(return_value=None),
    )
    entry = SimpleNamespace(id=uuid4(), lease_owner=None)

    async def reserve(**kwargs):
        entry.lease_owner = kwargs["lease_owner"]
        return entry, True

    cache = SimpleNamespace(
        get_ready=AsyncMock(return_value=None),
        reserve=AsyncMock(side_effect=reserve),
        get_for_update=AsyncMock(return_value=entry),
        release_failed=AsyncMock(),
    )
    db = SimpleNamespace(rollback=AsyncMock(), commit=AsyncMock())
    generator = Mock(side_effect=RuntimeError("provider"))

    with pytest.raises(RuntimeError, match="provider"):
        await GenerationMemoryService(db, cache).generate(
            content_type="assessment",
            context={"subject": "Python", "objective": None},
            topic_field="subject",
            schema=GeneratedAssessmentPayload,
            generator=generator,
        )

    cache.release_failed.assert_awaited_once_with(entry, "generation_failed")


@pytest.mark.anyio
async def test_alias_reuses_questions_but_different_objective_does_not(
    monkeypatch,
):
    monkeypatch.setattr(Env, "AI_MEMORY_ENABLED", True)
    monkeypatch.setattr(Env, "AI_MEMORY_REDIS_LOCK_ENABLED", False)
    monkeypatch.setattr(
        "sidebrain_back.services.generation_memory_service."
        "TopicAliasRepository.get_active_by_alias",
        AsyncMock(
            side_effect=lambda topic: (
                SimpleNamespace(canonical_topic="lingua inglesa")
                if topic == "ingles"
                else None
            )
        ),
    )
    entries = {}

    async def get_ready(fingerprint, content_type):
        entry = entries.get((fingerprint, content_type))
        return entry if entry and entry.payload is not None else None

    async def reserve(**kwargs):
        entry = SimpleNamespace(
            id=uuid4(), lease_owner=kwargs["lease_owner"], payload=None
        )
        entries[(kwargs["fingerprint"], kwargs["content_type"])] = entry
        return entry, True

    async def get_for_update(fingerprint, content_type):
        return entries.get((fingerprint, content_type))

    async def publish_ready(entry, payload):
        entry.payload = payload

    cache = SimpleNamespace(
        get_ready=AsyncMock(side_effect=get_ready),
        reserve=AsyncMock(side_effect=reserve),
        get_for_update=AsyncMock(side_effect=get_for_update),
        publish_ready=AsyncMock(side_effect=publish_ready),
    )
    db = SimpleNamespace(rollback=AsyncMock(), commit=AsyncMock())
    generator = Mock(return_value=assessment_payload())
    memory = GenerationMemoryService(db, cache)

    async def generate(subject, objective):
        return await memory.generate(
            content_type="assessment",
            context={"subject": subject, "objective": objective},
            topic_field="subject",
            schema=GeneratedAssessmentPayload,
            generator=generator,
        )

    first, first_source, _ = await generate("Inglês", "Viagem")
    second, second_source, _ = await generate("língua inglesa", "Viagem")
    _, third_source, _ = await generate("Inglês", "Negócios")

    assert first == second
    assert (first_source, second_source, third_source) == ("ai", "cache", "ai")
    assert generator.call_count == 2


@pytest.mark.anyio
async def test_cached_questions_create_separate_user_objects():
    repository = KnowledgeAssessmentRepository(
        SimpleNamespace(flush=AsyncMock())
    )
    first = SimpleNamespace(
        kas_id=uuid4(), kas_status=KnowledgeAssessmentStatusEnum.PENDING
    )
    second = SimpleNamespace(
        kas_id=uuid4(), kas_status=KnowledgeAssessmentStatusEnum.PENDING
    )
    payload = assessment_payload()

    await repository.mark_generated(first, payload)
    await repository.mark_generated(second, payload)

    assert {q.kaq_id for q in first.questions}.isdisjoint(
        {q.kaq_id for q in second.questions}
    )
    first_alternatives = {
        alternative.kaa_id
        for question in first.questions
        for alternative in question.alternatives
    }
    second_alternatives = {
        alternative.kaa_id
        for question in second.questions
        for alternative in question.alternatives
    }
    assert first_alternatives.isdisjoint(second_alternatives)
    assert all(
        sum(a.kaa_is_correct for a in q.alternatives) == 1
        for q in first.questions + second.questions
    )


@pytest.mark.anyio
async def test_cache_error_falls_back_to_provider(monkeypatch):
    monkeypatch.setattr(Env, "AI_MEMORY_ENABLED", True)
    monkeypatch.setattr(Env, "AI_MEMORY_REDIS_LOCK_ENABLED", False)
    monkeypatch.setattr(
        "sidebrain_back.services.generation_memory_service."
        "TopicAliasRepository.get_active_by_alias",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )
    payload = assessment_payload()
    generator = Mock(return_value=payload)
    db = SimpleNamespace(rollback=AsyncMock())

    result, source, cache_id = await GenerationMemoryService(
        db, SimpleNamespace()
    ).generate(
        content_type="assessment",
        context={"subject": "Python", "objective": None},
        topic_field="subject",
        schema=GeneratedAssessmentPayload,
        generator=generator,
    )

    assert (result, source, cache_id) == (payload, "ai", None)
    generator.assert_called_once()
