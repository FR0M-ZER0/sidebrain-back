from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select

from sidebrain_back.models import MissionProgress, Track
from sidebrain_back.repositories.mission_repository import MissionRepository
from sidebrain_back.schemas.mission_schema import MissionListParams
from sidebrain_back.services.mission_service import MissionService


@pytest.fixture
async def mission_listing(
    db_session,
    learning_hierarchy_factory,
    step_factory,
    mission_factory,
    mission_progress_factory,
    user_factory,
):
    h = await learning_hierarchy_factory()
    user_id = h.user.usr_id
    second_track = Track(
        trk_id=uuid4(),
        trk_user_id=user_id,
        trk_title="JavaScript",
        trk_icon="📘",
    )
    db_session.add(second_track)
    await db_session.flush()
    second_step = await step_factory(second_track, title="Async")
    idle = await mission_factory(h.step, title="Conclua 33%_ da etapa")
    active = await mission_factory(
        h.step, difficulty="hard", criteria="complete_a_step", criteria_value=1
    )
    done = await mission_factory(h.step)
    second = await mission_factory(second_step, title="Conclua a etapa Async")
    start = datetime(2026, 1, 1)
    for mission, day in ((idle, 2), (active, 1), (done, 1), (second, 3)):
        mission.msn_updated_at = start + timedelta(days=day)
    await mission_progress_factory(
        h.user,
        active,
        status="in_progress",
        score=66,
        updated_at=start + timedelta(days=10),
    )
    await mission_progress_factory(
        h.user,
        done,
        status="done",
        score=100,
        updated_at=start + timedelta(days=5),
    )
    # Progresso de outro usuário não filtra, ordena ou vaza na resposta.
    foreign = await user_factory()
    await mission_progress_factory(
        foreign,
        idle,
        status="done",
        score=100,
        updated_at=start + timedelta(days=100),
    )
    deleted_mission = await mission_factory(h.step, deleted=True)
    deleted_step = await step_factory(h.track, deleted=True)
    await mission_factory(deleted_step)
    deleted_track = Track(
        trk_id=uuid4(),
        trk_user_id=user_id,
        trk_title="Deleted",
        trk_is_deleted=True,
    )
    db_session.add(deleted_track)
    await db_session.flush()
    await mission_factory(await step_factory(deleted_track))
    other_h = await learning_hierarchy_factory()
    await mission_factory(other_h.step)
    await db_session.flush()
    return SimpleNamespace(
        user=h.user,
        track_id=h.track.trk_id,
        second_track_id=second_track.trk_id,
        foreign_track_id=other_h.track.trk_id,
        idle=idle,
        active=active,
        done=done,
        second=second,
        deleted_id=deleted_mission.msn_id,
        step=h.step,
        service=MissionService(MissionRepository(db_session), db_session),
    )


def mission_ids(page):
    return [m.id for group in page.data for m in group.missions]


@pytest.mark.anyio
async def test_missions_are_paginated_before_grouping_by_track(
    mission_listing,
):
    f = mission_listing
    first = await f.service.list_missions(
        f.user, MissionListParams(page_size=2)
    )
    assert (first.total_items, first.total_pages, first.page_size) == (4, 2, 2)
    assert len(first.data) == 1
    assert first.data[0].track_id == f.track_id
    assert mission_ids(first) == [f.active.msn_id, f.done.msn_id]
    assert first.data[0].missions[0].score == 66
    assert first.data[0].missions[0].status == "in_progress"
    assert first.data[0].missions[0].step_title == "Fundamentos"
    second = await f.service.list_missions(
        f.user, MissionListParams(page=2, page_size=2)
    )
    assert [group.track_id for group in second.data] == [
        f.second_track_id,
        f.track_id,
    ]
    assert mission_ids(second) == [f.second.msn_id, f.idle.msn_id]
    idle = second.data[1].missions[0]
    assert (idle.status, idle.score, idle.mission_progresses) == (
        "idle",
        0,
        [],
    )
    assert second.data[0].track_title == "JavaScript"
    assert second.data[0].track_icon == "📘"
    beyond = await f.service.list_missions(
        f.user, MissionListParams(page=3, page_size=2)
    )
    assert beyond.data == []
    assert beyond.total_items == 4


@pytest.mark.anyio
async def test_filters_combine_and_include_missing_progress_as_idle(
    mission_listing, db_session
):
    f = mission_listing
    expected = {
        "idle": {f.idle.msn_id, f.second.msn_id},
        "in_progress": {f.active.msn_id},
        "done": {f.done.msn_id},
    }
    for status, ids in expected.items():
        page = await f.service.list_missions(
            f.user, MissionListParams(status=status)
        )
        assert set(mission_ids(page)) == ids
        assert page.total_items == len(ids)
    matching = await f.service.list_missions(
        f.user,
        MissionListParams(
            status="in_progress",
            track_id=f.track_id,
            difficulty="hard",
            criteria="complete_a_step",
        ),
    )
    assert mission_ids(matching) == [f.active.msn_id]
    empty = await f.service.list_missions(
        f.user, MissionListParams(status="done", difficulty="hard")
    )
    assert (empty.data, empty.total_items, empty.total_pages) == ([], 0, 0)
    literal_search = await f.service.list_missions(
        f.user, MissionListParams(q="  33%_  ")
    )
    assert mission_ids(literal_search) == [f.idle.msn_id]
    case_insensitive = await f.service.list_missions(
        f.user, MissionListParams(q="async")
    )
    assert mission_ids(case_insensitive) == [f.second.msn_id]
    for track_id in (f.foreign_track_id, uuid4()):
        page = await f.service.list_missions(
            f.user, MissionListParams(track_id=track_id)
        )
        assert page.data == []
        assert page.total_items == 0
    # Ler a listagem não cria progresso para missões sem atividade.
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(MissionProgress)
            .where(
                MissionProgress.mpg_mission_id == f.idle.msn_id,
                MissionProgress.mpg_user_id == f.user.usr_id,
            )
        )
        == 0
    )


@pytest.mark.anyio
async def test_oldest_sort_and_uuid_tie_breaking(mission_listing, db_session):
    f = mission_listing
    page = await f.service.list_missions(
        f.user, MissionListParams(sort="oldest", page_size=1)
    )
    assert mission_ids(page) == [f.idle.msn_id]
    f.second.msn_updated_at = f.idle.msn_updated_at
    await db_session.flush()
    expected = sorted([f.idle.msn_id, f.second.msn_id])
    for page_number, mission_id in enumerate(expected, start=1):
        page = await f.service.list_missions(
            f.user,
            MissionListParams(
                status="idle", sort="oldest", page=page_number, page_size=1
            ),
        )
        assert mission_ids(page) == [mission_id]


@pytest.mark.anyio
async def test_query_count_is_constant(
    mission_listing, db_session, mission_factory
):
    f = mission_listing
    statements = []

    def collect(_conn, _cursor, statement, *_args):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    connection = await db_session.connection()
    event.listen(connection.sync_connection, "before_cursor_execute", collect)
    try:
        await f.service.list_missions(f.user, MissionListParams())
        assert len(statements) == 3
        for _ in range(20):
            await mission_factory(f.step)
        statements.clear()
        await f.service.list_missions(f.user, MissionListParams(page_size=100))
        assert len(statements) == 3
    finally:
        event.remove(
            connection.sync_connection, "before_cursor_execute", collect
        )
