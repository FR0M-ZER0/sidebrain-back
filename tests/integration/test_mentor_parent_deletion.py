from uuid import uuid4

import pytest
from sqlalchemy import select

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.mentor_conversation_model import MentorConversation
from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
)
from sidebrain_back.repositories.mentor_conversation_repository import (
    MentorConversationRepository,
)
from sidebrain_back.repositories.mentor_generation_repository import (
    MentorGenerationRepository,
)
from sidebrain_back.repositories.track_repository import TrackRepository
from sidebrain_back.repositories.user_repository import UserRepository
from sidebrain_back.services.mentor_consent_service import (
    MentorConsentUnavailable,
)
from sidebrain_back.services.mentor_privacy_service import MentorPrivacyService
from sidebrain_back.services.track_service import TrackService
from sidebrain_back.services.user_service import UserService


@pytest.mark.anyio
async def test_track_deletion_refuses_inflight_mentor_send(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user = hierarchy.user
    user_id = user.usr_id
    track_id = hierarchy.track.trk_id
    conversations = MentorConversationRepository(db_session)
    conversation = await conversations.create(user_id, track_id)
    conversation_id = conversation.id
    generations = MentorGenerationRepository(db_session)
    generation = await generations.create(conversation_id, uuid4(), "Ajuda")
    consent = MentorConsentRepository(db_session)
    await consent.accept(user_id, "v1")
    reservation = await generations.reserve(user_id, generation.id, "v1")
    reservation_id = reservation.id
    await db_session.commit()
    service = TrackService(
        TrackRepository(db_session),
        db_session,
        mentor_privacy_service=MentorPrivacyService(consent, db_session),
        mentor_conversations=conversations,
    )

    with pytest.raises(ProblemDetailError) as failure:
        await service.delete_track(user, track_id)
    assert failure.value.status_code == 503
    stored = await db_session.scalar(
        select(MentorConversation.id).where(
            MentorConversation.id == conversation_id
        )
    )
    assert stored == conversation_id

    from sidebrain_back.models.mentor_generation_model import (
        MentorSendReservation,
    )

    reservation = await db_session.get(MentorSendReservation, reservation_id)
    reservation.status = "finished"
    await db_session.commit()
    await db_session.refresh(user)
    await service.delete_track(user, track_id)
    assert await db_session.get(MentorConversation, conversation_id) is None


@pytest.mark.anyio
async def test_user_deletion_refuses_inflight_mentor_send(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user = hierarchy.user
    user_id = user.usr_id
    conversations = MentorConversationRepository(db_session)
    conversation = await conversations.create(user_id, hierarchy.track.trk_id)
    conversation_id = conversation.id
    generations = MentorGenerationRepository(db_session)
    generation = await generations.create(conversation_id, uuid4(), "Ajuda")
    consent = MentorConsentRepository(db_session)
    await consent.accept(user_id, "v1")
    reservation = await generations.reserve(user_id, generation.id, "v1")
    reservation_id = reservation.id
    await db_session.commit()
    service = UserService(
        UserRepository(db_session),
        db_session,
        mentor_privacy_service=MentorPrivacyService(consent, db_session),
        mentor_conversations=conversations,
    )

    with pytest.raises(MentorConsentUnavailable):
        await service.delete_user(user)
    from sidebrain_back.models.mentor_generation_model import (
        MentorSendReservation,
    )

    reservation = await db_session.get(MentorSendReservation, reservation_id)
    reservation.status = "finished"
    await db_session.commit()
    await db_session.refresh(user)
    await service.delete_user(user)
    assert await db_session.get(MentorConversation, conversation_id) is None
