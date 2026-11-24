import pytest

from sidebrain_back.repositories.mentor_conversation_repository import (
    MentorConversationRepository,
)


@pytest.mark.anyio
async def test_conversation_access_requires_owner_and_active_track(
    db_session, learning_hierarchy_factory, user_factory
):
    hierarchy = await learning_hierarchy_factory()
    other = await user_factory()
    repository = MentorConversationRepository(db_session)

    conversation = await repository.create(
        hierarchy.user.usr_id, hierarchy.track.trk_id
    )
    assert conversation is not None
    assert await repository.get(hierarchy.user.usr_id, conversation.id)
    assert await repository.get(other.usr_id, conversation.id) is None

    hierarchy.track.trk_is_deleted = True
    await db_session.flush()
    assert await repository.get(hierarchy.user.usr_id, conversation.id) is None
    assert (
        await repository.create(other.usr_id, hierarchy.track.trk_id) is None
    )
