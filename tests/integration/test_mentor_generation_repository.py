from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
)
from sidebrain_back.repositories.mentor_conversation_repository import (
    MentorConversationRepository,
)
from sidebrain_back.repositories.mentor_generation_repository import (
    MentorGenerationConflict,
    MentorGenerationRepository,
)


@pytest.mark.anyio
async def test_generation_is_idempotent_and_requires_single_active_turn(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    conversation = await MentorConversationRepository(db_session).create(
        hierarchy.user.usr_id, hierarchy.track.trk_id
    )
    repository = MentorGenerationRepository(db_session)
    key = uuid4()
    created = await repository.create(conversation.id, key, "Como estudar?")
    repeated = await repository.create(conversation.id, key, "Como estudar?")
    assert repeated.id == created.id

    with pytest.raises(MentorGenerationConflict):
        await repository.create(conversation.id, key, "Outro texto")
    with pytest.raises(MentorGenerationConflict):
        await repository.create(conversation.id, uuid4(), "Outra mensagem")


@pytest.mark.anyio
async def test_reservation_requires_consent_and_publish_is_complete(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    conversation = await MentorConversationRepository(db_session).create(
        hierarchy.user.usr_id, hierarchy.track.trk_id
    )
    repository = MentorGenerationRepository(db_session)
    generation = await repository.create(
        conversation.id, uuid4(), "Como estudar?"
    )
    with pytest.raises(MentorGenerationConflict):
        await repository.reserve(hierarchy.user.usr_id, generation.id, "v1")

    await MentorConsentRepository(db_session).accept(
        hierarchy.user.usr_id, "v1"
    )
    reservation = await repository.reserve(
        hierarchy.user.usr_id, generation.id, "v1"
    )
    assert reservation.status == "in_flight"
    assert generation.status == "processing"
    answer = await repository.complete(
        hierarchy.user.usr_id,
        generation.id,
        reservation.attempt_id,
        "Revise os fundamentos.",
        "v1",
    )
    assert answer.content == "Revise os fundamentos."
    assert answer.sequence == 2
    assert generation.status == "completed"
    assert reservation.status == "finished"


@pytest.mark.anyio
async def test_blocked_or_stale_generation_never_publishes(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    conversation = await MentorConversationRepository(db_session).create(
        user_id, hierarchy.track.trk_id
    )
    repository = MentorGenerationRepository(db_session)
    generation = await repository.create(conversation.id, uuid4(), "Estudar?")
    privacy = MentorConsentRepository(db_session)
    await privacy.accept(user_id, "v1")
    reservation = await repository.reserve(user_id, generation.id, "v1")

    assert (
        await repository.complete(
            user_id, generation.id, uuid4(), "Resposta antiga", "v1"
        )
        is None
    )
    assert reservation.status == "in_flight"
    block = await privacy.lock_privacy(user_id)
    block.blocked = True
    block.reason = "deletion"
    assert (
        await repository.complete(
            user_id, generation.id, reservation.attempt_id, "Resposta", "v1"
        )
        is None
    )
    assert reservation.status == "finished"
    assert generation.status == "failed"


@pytest.mark.anyio
async def test_expired_attempt_with_unresolved_send_fails_closed(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    conversation = await MentorConversationRepository(db_session).create(
        user_id, hierarchy.track.trk_id
    )
    repository = MentorGenerationRepository(db_session)
    generation = await repository.create(conversation.id, uuid4(), "Estudar?")
    await MentorConsentRepository(db_session).accept(user_id, "v1")
    reservation = await repository.reserve(user_id, generation.id, "v1")
    attempt_id = reservation.attempt_id
    generation.attempt_deadline = datetime.now(UTC).replace(
        tzinfo=None
    ) - timedelta(seconds=1)
    await db_session.flush()

    await repository.reconcile_expired(
        user_id, generation.id, attempt_id, "v1"
    )
    assert generation.status == "failed"
    assert reservation.status == "in_flight"
    assert (
        await repository.complete(
            user_id, generation.id, attempt_id, "Resposta tardia", "v1"
        )
        is None
    )


@pytest.mark.anyio
async def test_retry_reuses_original_message_and_is_idempotent(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    conversation = await MentorConversationRepository(db_session).create(
        hierarchy.user.usr_id, hierarchy.track.trk_id
    )
    repository = MentorGenerationRepository(db_session)
    original = await repository.create(conversation.id, uuid4(), "Estudar?")
    original.status = "failed"
    await db_session.flush()
    key = uuid4()

    retried = await repository.retry(conversation.id, original.id, key)
    repeated = await repository.retry(conversation.id, original.id, key)
    assert retried.id == repeated.id
    assert retried.student_message_id == original.student_message_id
    assert retried.status == "queued"
    retried.status = "failed"
    await db_session.flush()
    with pytest.raises(MentorGenerationConflict):
        await repository.retry(conversation.id, retried.id, key)
