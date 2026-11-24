from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
)
from sidebrain_back.repositories.mentor_conversation_repository import (
    MentorConversationRepository,
)
from sidebrain_back.repositories.mentor_generation_repository import (
    MentorGenerationRepository,
)
from sidebrain_back.services.mentor_consent_service import MentorConsentService
from sidebrain_back.services.mentor_processing_service import (
    MentorProcessingService,
)


@pytest.mark.anyio
async def test_processing_reserves_and_publishes_once(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    conversation = await MentorConversationRepository(db_session).create(
        user_id, hierarchy.track.trk_id
    )
    conversation_id = conversation.id
    generations = MentorGenerationRepository(db_session)
    generation = await generations.create(
        conversation.id, uuid4(), "Como estudar?"
    )
    generation_id = generation.id
    consent = MentorConsentService(
        MentorConsentRepository(db_session), db_session
    )
    notice = await consent.get_mentor_consent(user_id)
    await consent.accept_mentor_consent(user_id, notice.notice_version)

    generator = Mock()
    generator.generate_mentor_response = AsyncMock()
    generator.generate_mentor_response.return_value = "Revise os fundamentos."
    service = MentorProcessingService(db_session, generator)
    await service.process(user_id, generation_id)
    await service.process(user_id, generation_id)

    assert generator.generate_mentor_response.call_count == 1
    result = await generations.get(user_id, conversation_id, generation_id)
    assert result.status == "completed"
    assert await generations.get_response_id(generation_id)


@pytest.mark.anyio
async def test_provider_timeout_requeues_without_partial_response(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    conversation = await MentorConversationRepository(db_session).create(
        user_id, hierarchy.track.trk_id
    )
    conversation_id = conversation.id
    generations = MentorGenerationRepository(db_session)
    generation = await generations.create(
        conversation_id, uuid4(), "Como estudar?"
    )
    generation_id = generation.id
    consent = MentorConsentService(
        MentorConsentRepository(db_session), db_session
    )
    notice = await consent.get_mentor_consent(user_id)
    await consent.accept_mentor_consent(user_id, notice.notice_version)
    generator = Mock()
    generator.generate_mentor_response = AsyncMock()
    generator.generate_mentor_response.side_effect = TimeoutError()

    service = MentorProcessingService(db_session, generator)
    await service.process(user_id, generation_id)

    result = await generations.get(user_id, conversation_id, generation_id)
    assert result.status == "queued"
    assert result.attempt_count == 1
    assert await generations.get_response_id(generation_id) is None
    assert not await MentorConsentRepository(db_session).has_inflight(user_id)

    await service.process(user_id, generation_id)
    await service.process(user_id, generation_id)
    await service.process(user_id, generation_id)
    result = await generations.get(user_id, conversation_id, generation_id)
    assert result.status == "failed"
    assert result.attempt_count == 3
    assert generator.generate_mentor_response.call_count == 3


@pytest.mark.anyio
async def test_revoked_consent_prevents_queued_provider_call(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    conversation = await MentorConversationRepository(db_session).create(
        user_id, hierarchy.track.trk_id
    )
    conversation_id = conversation.id
    generations = MentorGenerationRepository(db_session)
    generation = await generations.create(
        conversation_id, uuid4(), "Como estudar?"
    )
    generation_id = generation.id
    consent = MentorConsentService(
        MentorConsentRepository(db_session), db_session
    )
    notice = await consent.get_mentor_consent(user_id)
    await consent.accept_mentor_consent(user_id, notice.notice_version)
    await consent.revoke_mentor_consent(user_id)
    generator = Mock()
    generator.generate_mentor_response = AsyncMock()

    await MentorProcessingService(db_session, generator).process(
        user_id, generation_id
    )

    generator.generate_mentor_response.assert_not_called()
    result = await generations.get(user_id, conversation_id, generation_id)
    assert result.status == "failed"
    assert result.error_code == "consent_required"


@pytest.mark.anyio
async def test_provider_context_excludes_other_users_and_tracks(
    db_session,
    learning_hierarchy_factory,
    user_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()
    second = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    second.track.trk_user_id = user_id
    await db_session.flush()
    other_user = await user_factory()
    current_quiz = await quiz_factory(hierarchy.lesson)
    other_quiz = await quiz_factory(second.lesson)
    await answer_factory(current_quiz, hierarchy.user, reason="Dados próprios")
    await answer_factory(current_quiz, other_user, reason="Dados de terceiro")
    await answer_factory(other_quiz, hierarchy.user, reason="Outra trilha")
    conversation = await MentorConversationRepository(db_session).create(
        user_id, hierarchy.track.trk_id
    )
    generation = await MentorGenerationRepository(db_session).create(
        conversation.id, uuid4(), "Como melhorar?"
    )
    generation_id = generation.id
    consent = MentorConsentService(
        MentorConsentRepository(db_session), db_session
    )
    notice = await consent.get_mentor_consent(user_id)
    await consent.accept_mentor_consent(user_id, notice.notice_version)
    generator = Mock()
    generator.generate_mentor_response = AsyncMock()
    captured = {}

    async def generate(message, get_tool_data, *, history):
        captured["message"] = message
        captured["history"] = history
        captured["context"] = await get_tool_data("consultar_avaliacoes")
        return "Pratique os fundamentos."

    generator.generate_mentor_response.side_effect = generate

    await MentorProcessingService(db_session, generator).process(
        user_id, generation_id
    )

    assert captured["message"] == "Como melhorar?"
    assert captured["history"] == []
    context = str(captured["context"])
    assert "Dados próprios" in context
    assert "Dados de terceiro" not in context
    assert "Outra trilha" not in context


@pytest.mark.anyio
async def test_lost_lock_after_send_keeps_reservation_inconclusive(
    db_session, learning_hierarchy_factory, monkeypatch
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    conversation = await MentorConversationRepository(db_session).create(
        user_id, hierarchy.track.trk_id
    )
    conversation_id = conversation.id
    generations = MentorGenerationRepository(db_session)
    generation = await generations.create(
        conversation_id, uuid4(), "Como estudar?"
    )
    generation_id = generation.id
    consent_repo = MentorConsentRepository(db_session)
    consent = MentorConsentService(consent_repo, db_session)
    notice = await consent.get_mentor_consent(user_id)
    await consent.accept_mentor_consent(user_id, notice.notice_version)
    generator = Mock()
    generator.generate_mentor_response = AsyncMock()
    generator.generate_mentor_response.return_value = "Uma orientação."
    service = MentorProcessingService(db_session, generator)
    monkeypatch.setattr(
        service,
        "_check_lock_connection",
        AsyncMock(side_effect=[None, RuntimeError("perdido"), RuntimeError()]),
    )

    with pytest.raises(RuntimeError):
        await service.process(user_id, generation_id)

    assert await consent_repo.has_inflight(user_id)
    assert await generations.get_response_id(generation_id) is None


@pytest.mark.anyio
async def test_provider_exception_does_not_leak_content_to_logs(
    db_session, learning_hierarchy_factory, caplog
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    conversation = await MentorConversationRepository(db_session).create(
        user_id, hierarchy.track.trk_id
    )
    secret = "conteudo-privado-sintetico-mentoria"
    generation = await MentorGenerationRepository(db_session).create(
        conversation.id, uuid4(), secret
    )
    generation_id = generation.id
    consent = MentorConsentService(
        MentorConsentRepository(db_session), db_session
    )
    notice = await consent.get_mentor_consent(user_id)
    await consent.accept_mentor_consent(user_id, notice.notice_version)
    generator = Mock()
    generator.generate_mentor_response = AsyncMock()
    generator.generate_mentor_response.side_effect = ValueError(secret)

    with caplog.at_level("INFO"):
        await MentorProcessingService(db_session, generator).process(
            user_id, generation_id
        )

    assert secret not in caplog.text
    assert "error_type=ValueError" in caplog.text
    assert f"generation_id={generation_id}" in caplog.text
