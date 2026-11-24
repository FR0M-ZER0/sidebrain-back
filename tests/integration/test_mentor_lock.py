from uuid import uuid4

import pytest
from sqlalchemy import select

from sidebrain_back.core.mentor_lock import mentor_user_lock
from sidebrain_back.models.mentor_conversation_model import MentorConversation
from sidebrain_back.models.mentor_generation_model import (
    MentorGeneration,
    MentorPrivacyBlock,
    MentorSendReservation,
)
from sidebrain_back.models.mentor_message_model import MentorMessage
from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
)
from sidebrain_back.services.mentor_consent_service import (
    MentorConsentService,
    MentorConsentUnavailable,
)
from sidebrain_back.services.mentor_privacy_service import MentorPrivacyService


@pytest.mark.anyio
async def test_lock_serializes_the_same_user_and_allows_another(db_session):
    user_id = uuid4()
    async with mentor_user_lock(user_id, wait_seconds=1):
        async with mentor_user_lock(uuid4(), wait_seconds=1):
            pass
        with pytest.raises(TimeoutError):
            async with mentor_user_lock(user_id, wait_seconds=0.05):
                pass

    async with mentor_user_lock(user_id, wait_seconds=1):
        pass


@pytest.mark.anyio
async def test_lock_is_released_when_body_raises(db_session):
    user_id = uuid4()
    with pytest.raises(ValueError):
        async with mentor_user_lock(user_id, wait_seconds=1):
            raise ValueError("interrompido")

    async with mentor_user_lock(user_id, wait_seconds=1):
        pass


@pytest.mark.anyio
async def test_lost_lock_does_not_clear_inflight_privacy_reservation(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    user_id = hierarchy.user.usr_id
    conversation = MentorConversation(
        id=uuid4(), user_id=user_id, track_id=hierarchy.track.trk_id
    )
    db_session.add(conversation)
    await db_session.flush()
    message = MentorMessage(
        id=uuid4(),
        conversation_id=conversation.id,
        sequence=1,
        role="student",
        content="Preciso de orientação.",
    )
    db_session.add(message)
    await db_session.flush()
    generation = MentorGeneration(
        id=uuid4(),
        conversation_id=conversation.id,
        student_message_id=message.id,
        idempotency_key=uuid4(),
    )
    db_session.add(generation)
    await db_session.flush()
    reservation = MentorSendReservation(
        id=uuid4(),
        user_id=user_id,
        generation_id=generation.id,
        attempt_id=uuid4(),
        status="in_flight",
    )
    db_session.add(reservation)
    await db_session.flush()
    service = MentorConsentService(
        MentorConsentRepository(db_session), db_session, wait_seconds=0
    )

    with pytest.raises(RuntimeError, match="Conexão do bloqueio"):
        async with mentor_user_lock(user_id, wait_seconds=1) as connection:
            await connection.invalidate()
            with pytest.raises(MentorConsentUnavailable):
                await service.revoke_mentor_consent(user_id)

    block = await db_session.scalar(
        select(MentorPrivacyBlock).where(MentorPrivacyBlock.user_id == user_id)
    )
    assert block.blocked is True
    assert block.reason == "revocation"
    assert reservation.status == "in_flight"


@pytest.mark.anyio
async def test_deletion_keeps_block_during_inconclusive_send(
    db_session, user_factory, monkeypatch
):
    user = await user_factory()
    user_id = user.usr_id
    repo = MentorConsentRepository(db_session)
    service = MentorPrivacyService(repo, db_session)

    async def inflight(_user_id):
        return True

    monkeypatch.setattr(repo, "has_inflight", inflight)
    with pytest.raises(MentorConsentUnavailable):
        await service.lock_for_deletion(user_id)

    block = await db_session.scalar(
        select(MentorPrivacyBlock).where(MentorPrivacyBlock.user_id == user_id)
    )
    assert block.blocked is True
    assert block.reason == "deletion"

    async def finished(_user_id):
        return False

    monkeypatch.setattr(repo, "has_inflight", finished)
    block = await service.lock_for_deletion(user_id)
    assert block.blocked is True
    block.blocked = False
    block.reason = None
    await db_session.commit()
