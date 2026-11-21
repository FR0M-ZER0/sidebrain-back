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
    MentorGenerationRepository,
)
from sidebrain_back.services.mentor_consent_service import MentorConsentService
from sidebrain_back.services.mentor_dispatch_service import (
    MentorDispatchService,
)


@pytest.mark.anyio
async def test_dispatch_recovers_queue_and_fails_closed_on_expired_send(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    conversation = await MentorConversationRepository(db_session).create(
        user_id, hierarchy.track.trk_id
    )
    conversation_id = conversation.id
    repository = MentorGenerationRepository(db_session)
    generation = await repository.create(conversation_id, uuid4(), "Estudar?")
    generation_id = generation.id
    consent = MentorConsentService(
        MentorConsentRepository(db_session), db_session
    )
    notice = await consent.get_mentor_consent(user_id)
    await consent.accept_mentor_consent(user_id, notice.notice_version)
    dispatcher = MentorDispatchService(db_session)
    queued = await dispatcher.collect_pending()
    assert (str(user_id), str(generation_id)) in queued

    reservation = await repository.reserve(
        user_id, generation_id, notice.notice_version
    )
    generation = await repository.get(user_id, conversation_id, generation_id)
    generation.attempt_deadline = datetime.now(UTC).replace(
        tzinfo=None
    ) - timedelta(seconds=1)
    reservation_id = reservation.id
    await db_session.commit()

    queued = await dispatcher.collect_pending()
    assert (str(user_id), str(generation_id)) not in queued
    generation = await repository.get(user_id, conversation_id, generation_id)
    assert generation.status == "failed"
    assert await MentorConsentRepository(db_session).has_inflight(user_id)
    assert reservation_id


@pytest.mark.anyio
async def test_expired_processing_without_reservation_returns_to_queue(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    conversation = await MentorConversationRepository(db_session).create(
        user_id, hierarchy.track.trk_id
    )
    conversation_id = conversation.id
    repository = MentorGenerationRepository(db_session)
    generation = await repository.create(conversation_id, uuid4(), "Estudar?")
    generation_id = generation.id
    consent = MentorConsentService(
        MentorConsentRepository(db_session), db_session
    )
    notice = await consent.get_mentor_consent(user_id)
    await consent.accept_mentor_consent(user_id, notice.notice_version)
    generation.status = "processing"
    generation.attempt_id = uuid4()
    generation.attempt_count = 1
    generation.attempt_deadline = datetime.now(UTC).replace(
        tzinfo=None
    ) - timedelta(seconds=1)
    await db_session.commit()

    queued = await MentorDispatchService(db_session).collect_pending()
    assert (str(user_id), str(generation_id)) in queued
    generation = await repository.get(user_id, conversation_id, generation_id)
    assert generation.status == "queued"
    assert generation.attempt_id is None
