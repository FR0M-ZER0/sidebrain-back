from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.mission_progress_status_enum import (
    MissionProgressStatusEnum,
)
from sidebrain_back.models.track_model import Track
from sidebrain_back.repositories.ranking_repository import RankingRepository
from sidebrain_back.services.ranking_service import RankingService


@pytest.mark.anyio
async def test_ranking_lifecycle_and_eligibility(
    db_session,
    learning_hierarchy_factory,
    step_factory,
    mission_factory,
    mission_progress_factory,
    user_factory,
):
    hierarchy = await learning_hierarchy_factory()
    user_1 = hierarchy.user

    user_2 = await user_factory(name="User 2")
    user_3 = await user_factory(name="User 3")
    user_deleted = await user_factory(name="Deleted User", deleted=True)

    mission_1 = await mission_factory(
        hierarchy.step, title="Mission 1", xp_reward=100
    )
    mission_2 = await mission_factory(
        hierarchy.step, title="Mission 2", xp_reward=200
    )
    mission_deleted = await mission_factory(
        hierarchy.step, title="Mission Deleted", xp_reward=500, deleted=True
    )

    # Trilha removida logicamente do próprio user_1, sem criar outro usuário
    deleted_track = Track(
        trk_id=uuid4(),
        trk_user_id=user_1.usr_id,
        trk_title="Deleted Track",
        trk_is_deleted=True,
        trk_deleted_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(deleted_track)
    await db_session.flush()
    step_under_deleted_track = await step_factory(deleted_track)
    mission_under_deleted_track = await mission_factory(
        step_under_deleted_track,
        title="Mission Under Deleted Track",
        xp_reward=50,
        deleted=False,
    )

    # User 1: mission_1 (100) + mission_2 (200) = 300 XP, 2 missions
    await mission_progress_factory(
        user_1, mission_1, status=MissionProgressStatusEnum.DONE
    )
    await mission_progress_factory(
        user_1, mission_2, status=MissionProgressStatusEnum.DONE
    )
    # User 1 also has in_progress on another mission (should NOT count)
    await mission_progress_factory(
        user_1,
        mission_under_deleted_track,
        status=MissionProgressStatusEnum.IN_PROGRESS,
    )

    # User 2: mission_under_deleted_track
    # (50 XP, track is deleted but mission active -> counts!)
    await mission_progress_factory(
        user_2,
        mission_under_deleted_track,
        status=MissionProgressStatusEnum.DONE,
    )
    # User 2 also completed a soft-deleted mission (should NOT count)
    await mission_progress_factory(
        user_2, mission_deleted, status=MissionProgressStatusEnum.DONE
    )

    # User deleted has high XP (should NOT appear)
    await mission_progress_factory(
        user_deleted, mission_1, status=MissionProgressStatusEnum.DONE
    )

    # User 3 has NO completed missions (0 XP, 0 missions)

    repo = RankingRepository(db_session)
    service = RankingService(repo)
    xp_summary = await repo.get_user_xp_summary(user_1.usr_id)
    assert xp_summary.xp == 300
    assert xp_summary.missions_completed == 2

    # Test list page 1
    page_1 = await service.list_rankings(page=1, page_size=2)
    assert page_1.total_items == 3
    assert page_1.total_pages == 2
    assert page_1.page == 1
    assert page_1.page_size == 2
    assert len(page_1.data) == 2

    assert page_1.data[0].user_id == user_1.usr_id
    assert page_1.data[0].position == 1
    assert page_1.data[0].xp == 300
    assert page_1.data[0].missions_completed == 2

    assert page_1.data[1].user_id == user_2.usr_id
    assert page_1.data[1].position == 2
    assert page_1.data[1].xp == 50
    assert page_1.data[1].missions_completed == 1

    # Test list page 2 (continuity of position)
    page_2 = await service.list_rankings(page=2, page_size=2)
    assert page_2.page == 2
    assert len(page_2.data) == 1
    assert page_2.data[0].user_id == user_3.usr_id
    assert page_2.data[0].position == 3
    assert page_2.data[0].xp == 0
    assert page_2.data[0].missions_completed == 0

    # Test individual ranking (GET /rankings/me)
    me_1 = await service.get_my_ranking(user_1)
    assert me_1.position == 1
    assert me_1.user_id == user_1.usr_id
    assert me_1.xp == 300
    assert me_1.missions_completed == 2

    me_2 = await service.get_my_ranking(user_2)
    assert me_2.position == 2
    assert me_2.user_id == user_2.usr_id
    assert me_2.xp == 50
    assert me_2.missions_completed == 1

    me_3 = await service.get_my_ranking(user_3)
    assert me_3.position == 3
    assert me_3.user_id == user_3.usr_id
    assert me_3.xp == 0
    assert me_3.missions_completed == 0

    # Deleted user raises 404
    with pytest.raises(ProblemDetailError) as exc_info:
        await service.get_my_ranking(user_deleted)
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_deterministic_tie_breaking(
    db_session,
    learning_hierarchy_factory,
    mission_factory,
    mission_progress_factory,
    user_factory,
):
    hierarchy = await learning_hierarchy_factory()
    mission = await mission_factory(
        hierarchy.step, title="Fixed 100 XP", xp_reward=100
    )

    t1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC).replace(tzinfo=None)
    t2 = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC).replace(tzinfo=None)

    id_small = UUID("00000000-0000-0000-0000-000000000001")
    id_large = UUID("00000000-0000-0000-0000-000000000002")

    user_a = await user_factory(user_id=id_large, name="User A", created_at=t1)
    user_b = await user_factory(user_id=uuid4(), name="User B", created_at=t2)
    user_c = await user_factory(user_id=id_small, name="User C", created_at=t1)

    for u in (user_a, user_b, user_c):
        await mission_progress_factory(
            u, mission, status=MissionProgressStatusEnum.DONE
        )

    repo = RankingRepository(db_session)
    service = RankingService(repo)

    result = await service.list_rankings(page=1, page_size=10)
    # Filter our 3 users
    our_entries = [
        item
        for item in result.data
        if item.user_id in (user_a.usr_id, user_b.usr_id, user_c.usr_id)
    ]
    assert len(our_entries) == 3
    # User C and User A tied on XP (100) and created_at (t1)
    # -> User C has smaller UUID
    assert our_entries[0].user_id == user_c.usr_id
    assert our_entries[1].user_id == user_a.usr_id
    # User B tied on XP (100) but created_at is newer (t2) -> after User A
    assert our_entries[2].user_id == user_b.usr_id

    # Verify positions are sequential and unique
    assert (
        our_entries[0].position
        < our_entries[1].position
        < our_entries[2].position
    )

    # Individual queries match exact position
    me_c = await service.get_my_ranking(user_c)
    me_a = await service.get_my_ranking(user_a)
    me_b = await service.get_my_ranking(user_b)
    assert me_c.position == our_entries[0].position
    assert me_a.position == our_entries[1].position
    assert me_b.position == our_entries[2].position


@pytest.mark.anyio
async def test_constant_query_count(
    db_session,
    learning_hierarchy_factory,
    user_factory,
):
    await learning_hierarchy_factory()
    for i in range(5):
        await user_factory(name=f"Batch User {i}")

    repo = RankingRepository(db_session)
    service = RankingService(repo)

    queries: list[str] = []

    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        queries.append(statement)

    event.listen(
        db_session.sync_session.bind,
        "before_cursor_execute",
        before_cursor_execute,
    )
    try:
        queries.clear()
        await service.list_rankings(page=1, page_size=2)
        assert len(queries) == 2, (
            f"Expected 2 queries for list, got {len(queries)}"
        )

        queries.clear()
        user = await user_factory(name="Target User")
        queries.clear()
        await service.get_my_ranking(user)
        assert len(queries) == 1, (
            f"Expected 1 query for me, got {len(queries)}"
        )
    finally:
        event.remove(
            db_session.sync_session.bind,
            "before_cursor_execute",
            before_cursor_execute,
        )
