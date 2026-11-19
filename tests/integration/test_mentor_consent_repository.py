import pytest

from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
)


@pytest.mark.anyio
async def test_consent_is_owned_and_can_be_revoked_and_reaccepted(
    db_session, user_factory
):
    first = await user_factory()
    second = await user_factory()
    repository = MentorConsentRepository(db_session)

    assert await repository.get(first.usr_id) is None
    consent = await repository.accept(first.usr_id, "v1")
    assert consent.notice_version == "v1"
    assert consent.revoked_at is None
    assert await repository.get(second.usr_id) is None

    await repository.revoke(first.usr_id)
    assert (await repository.get(first.usr_id)).revoked_at is not None

    updated = await repository.accept(first.usr_id, "v2")
    assert updated.id == consent.id
    assert updated.notice_version == "v2"
    assert updated.revoked_at is None
