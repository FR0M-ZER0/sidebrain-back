import pytest
from sqlalchemy import select

from sidebrain_back.core.constants import Env
from sidebrain_back.models.mentor_generation_model import MentorPrivacyBlock
from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
)
from sidebrain_back.services.auth_errors import ConflictError
from sidebrain_back.services.mentor_consent_service import (
    MentorConsentService,
    MentorConsentUnavailable,
)


@pytest.mark.anyio
async def test_consent_service_version_and_revocation(
    db_session, user_factory
):
    user = await user_factory()
    repo = MentorConsentRepository(db_session)
    service = MentorConsentService(repo, db_session, wait_seconds=0)

    assert not (await service.get_mentor_consent(user.usr_id)).authorized
    with pytest.raises(ConflictError):
        await service.accept_mentor_consent(user.usr_id, "outdated")
    version = (await service.get_mentor_consent(user.usr_id)).notice_version
    accepted = await service.accept_mentor_consent(user.usr_id, version)
    assert accepted.authorized
    await service.revoke_mentor_consent(user.usr_id)
    assert not (await service.get_mentor_consent(user.usr_id)).authorized


@pytest.mark.anyio
async def test_inflight_send_preserves_revocation_block(
    db_session, user_factory, monkeypatch
):
    user = await user_factory()
    repo = MentorConsentRepository(db_session)
    service = MentorConsentService(repo, db_session)
    version = (await service.get_mentor_consent(user.usr_id)).notice_version
    await service.accept_mentor_consent(user.usr_id, version)

    async def inflight(_user_id):
        return True

    monkeypatch.setattr(repo, "has_inflight", inflight)
    with pytest.raises(MentorConsentUnavailable):
        await service.revoke_mentor_consent(user.usr_id)
    block = await db_session.scalar(
        select(MentorPrivacyBlock).where(
            MentorPrivacyBlock.user_id == user.usr_id
        )
    )
    assert block.blocked is True
    assert block.reason == "revocation"
    assert not (await service.get_mentor_consent(user.usr_id)).authorized

    async def finished(_user_id):
        return False

    monkeypatch.setattr(repo, "has_inflight", finished)
    await service.revoke_mentor_consent(user.usr_id)
    assert not (await service.get_mentor_consent(user.usr_id)).authorized
    assert block.blocked is False


@pytest.mark.anyio
async def test_revocation_does_not_clear_pending_deletion_block(
    db_session, user_factory
):
    user = await user_factory()
    user_id = user.usr_id
    repo = MentorConsentRepository(db_session)
    service = MentorConsentService(repo, db_session, wait_seconds=0)
    block = await repo.lock_privacy(user_id)
    block.blocked = True
    block.reason = "deletion"
    await db_session.commit()

    with pytest.raises(MentorConsentUnavailable):
        await service.revoke_mentor_consent(user_id)

    stored = await db_session.scalar(
        select(MentorPrivacyBlock).where(MentorPrivacyBlock.user_id == user_id)
    )
    assert stored.blocked is True
    assert stored.reason == "deletion"


@pytest.mark.anyio
async def test_provider_change_requires_new_authorization(
    db_session, user_factory, monkeypatch
):
    user = await user_factory()
    service = MentorConsentService(
        MentorConsentRepository(db_session), db_session
    )
    monkeypatch.setattr(Env, "OPENAI_CHAT_API_KEY", None)
    monkeypatch.setattr(Env, "GROQ_API_KEY", "configured-groq")
    notice = await service.get_mentor_consent(user.usr_id)
    assert notice.recipient == "Groq"
    await service.accept_mentor_consent(user.usr_id, notice.notice_version)

    monkeypatch.setattr(Env, "OPENAI_CHAT_API_KEY", "configured-openai")
    changed = await service.get_mentor_consent(user.usr_id)
    assert changed.recipient == "OpenAI"
    assert changed.notice_version != notice.notice_version
    assert not changed.authorized
