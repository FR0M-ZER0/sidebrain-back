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
from sidebrain_back.schemas.mentor_schema import MentorMessageCreate
from sidebrain_back.services.mentor_consent_service import MentorConsentService
from sidebrain_back.services.mentor_privacy_service import MentorPrivacyService
from sidebrain_back.services.mentor_service import (
    MentorConsentRequired,
    MentorNotFound,
    MentorService,
)


@pytest.mark.anyio
async def test_submit_requires_authorization_and_preserves_ownership(
    db_session, learning_hierarchy_factory, user_factory
):
    hierarchy = await learning_hierarchy_factory()
    other = await user_factory()
    user_id = hierarchy.user.usr_id
    track_id = hierarchy.track.trk_id
    other_id = other.usr_id
    consent_repo = MentorConsentRepository(db_session)
    consent_service = MentorConsentService(consent_repo, db_session)
    service = MentorService(
        MentorConversationRepository(db_session),
        MentorGenerationRepository(db_session),
        consent_repo,
        consent_service,
        db_session,
    )
    conversation = await service.create_mentor_conversation(user_id, track_id)
    payload = MentorMessageCreate(content="Como estudar?")
    with pytest.raises(MentorConsentRequired):
        await service.create_mentor_message(
            user_id, conversation.id, uuid4(), payload
        )
    with pytest.raises(MentorNotFound):
        await service.create_mentor_conversation(other_id, track_id)

    notice = await consent_service.get_mentor_consent(user_id)
    await consent_service.accept_mentor_consent(user_id, notice.notice_version)
    key = uuid4()
    accepted = await service.create_mentor_message(
        user_id, conversation.id, key, payload
    )
    await MentorGenerationRepository(db_session).reserve(
        user_id, accepted.generation_id, notice.notice_version
    )
    await db_session.commit()
    repeated = await service.create_mentor_message(
        user_id, conversation.id, key, payload
    )
    assert accepted.generation_id == repeated.generation_id
    assert accepted.status == "queued"
    assert repeated.status == "processing"


@pytest.mark.anyio
async def test_delete_removes_only_own_conversations(
    db_session, learning_hierarchy_factory, user_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    track_id = hierarchy.track.trk_id
    other = await user_factory()
    other_id = other.usr_id
    consent_repo = MentorConsentRepository(db_session)
    conversations = MentorConversationRepository(db_session)
    service = MentorService(
        conversations,
        MentorGenerationRepository(db_session),
        consent_repo,
        MentorConsentService(consent_repo, db_session),
        db_session,
        MentorPrivacyService(consent_repo, db_session),
    )
    first = await service.create_mentor_conversation(user_id, track_id)
    second = await service.create_mentor_conversation(user_id, track_id)
    await MentorGenerationRepository(db_session).create(
        first.id, uuid4(), "Mensagem da primeira conversa"
    )
    await db_session.commit()
    first_messages = await service.list_mentor_messages(
        user_id, first.id, 1, 1
    )
    second_messages = await service.list_mentor_messages(
        user_id, second.id, 1, 1
    )
    assert first_messages.total_items == 1
    assert second_messages.total_items == 0
    with pytest.raises(MentorNotFound):
        await service.delete_mentor_conversations(other_id, first.id)
    await service.delete_mentor_conversations(user_id, first.id)
    assert await conversations.get(user_id, first.id) is None
    assert await conversations.get(user_id, second.id) is not None
    await service.delete_mentor_conversations(user_id)
    assert await conversations.get(user_id, second.id) is None
