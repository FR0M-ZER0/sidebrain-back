from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import event

from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.models.track_model import Track
from sidebrain_back.repositories.track_repository import TrackRepository
from sidebrain_back.schemas.track_schema import TrackListParams
from sidebrain_back.services.track_service import TrackService


@pytest.fixture
async def track_listing(
    db_session,
    learning_hierarchy_factory,
    step_factory,
    lesson_factory,
    quiz_factory,
    mission_factory,
    user_factory,
):
    hierarchy = await learning_hierarchy_factory()
    hierarchy.track.trk_title = "Python Basics"
    hierarchy.track.trk_description = "Programming introduction"
    hierarchy.track.trk_created_at = datetime(2026, 1, 2)
    hierarchy.track.trk_updated_at = datetime(2026, 1, 2)
    hierarchy.step.stp_title = "Python fundamentals"
    quiz = await quiz_factory(hierarchy.lesson, question="Variables")
    mission = await mission_factory(hierarchy.step, title="Complete Python")

    javascript = Track(
        trk_id=uuid4(),
        trk_user_id=hierarchy.user.usr_id,
        trk_title="JavaScript Web",
        trk_description="Frontend programming",
        trk_created_at=datetime(2026, 1, 3),
        trk_updated_at=datetime(2026, 1, 3),
        trk_is_deleted=False,
    )
    db_session.add(javascript)
    await db_session.flush()
    js_step = await step_factory(javascript, title="Async", flush=False)
    js_step.stp_level = StepLevelEnum.ADVANCED
    await db_session.flush()
    await lesson_factory(js_step, title="Promises", text="Async", flush=False)

    python_advanced = Track(
        trk_id=uuid4(),
        trk_user_id=hierarchy.user.usr_id,
        trk_title="Python Advanced",
        trk_description="Advanced Python",
        trk_created_at=datetime(2026, 1, 1),
        trk_updated_at=datetime(2026, 1, 1),
        trk_is_deleted=False,
    )
    db_session.add(python_advanced)
    await db_session.flush()
    advanced_step = await step_factory(
        python_advanced, deleted=True, flush=False
    )
    await lesson_factory(advanced_step, flush=False)

    foreign = await learning_hierarchy_factory()
    foreign.track.trk_title = "Python private"
    deleted = Track(
        trk_id=uuid4(),
        trk_user_id=hierarchy.user.usr_id,
        trk_title="Deleted Python",
        trk_is_deleted=True,
    )
    db_session.add(deleted)
    await db_session.flush()
    deleted_step = await step_factory(deleted, flush=False)
    await lesson_factory(deleted_step, flush=False)
    await mission_factory(deleted_step, flush=False)
    await db_session.flush()

    service = TrackService(TrackRepository(db_session), db_session)
    return (
        hierarchy,
        service,
        javascript,
        python_advanced,
        foreign,
        quiz,
        mission,
    )


@pytest.mark.anyio
async def test_track_list_returns_nested_content_and_user_owned_tracks(
    track_listing,
):
    hierarchy, service, javascript, _advanced, _foreign, quiz, mission = (
        track_listing
    )
    result = await service.list_tracks(
        hierarchy.user, TrackListParams(page=1, page_size=20)
    )

    assert result.total_items == 3
    tracks = {track.id: track for track in result.data}
    python = tracks[hierarchy.track.trk_id]
    assert python.steps[0].lessons[0].quizzes[0].id == quiz.qui_id
    assert python.steps[0].missions[0].id == mission.msn_id
    assert tracks[javascript.trk_id].steps[0].lessons[0].title == "Promises"


@pytest.mark.anyio
async def test_track_filters_combine_search_and_escape_wildcards(
    track_listing,
):
    hierarchy, service, javascript, python_advanced, _foreign, *_ = (
        track_listing
    )

    matching = await service.list_tracks(
        hierarchy.user,
        TrackListParams(q="PYTHON", level="beginner", has_missions=True),
    )
    assert [item.id for item in matching.data] == [hierarchy.track.trk_id]
    assert matching.total_items == 1

    advanced = await service.list_tracks(
        hierarchy.user, TrackListParams(level=StepLevelEnum.ADVANCED)
    )
    assert [item.id for item in advanced.data] == [javascript.trk_id]

    without_missions = await service.list_tracks(
        hierarchy.user, TrackListParams(has_missions=False)
    )
    assert {item.id for item in without_missions.data} == {
        javascript.trk_id,
        python_advanced.trk_id,
    }

    literal_search = await service.list_tracks(
        hierarchy.user, TrackListParams(q="100%_literal")
    )
    assert literal_search.data == []


@pytest.mark.anyio
async def test_track_sort_and_pagination_apply_after_filters(track_listing):
    hierarchy, service, javascript, python_advanced, *_ = track_listing

    newest = await service.list_tracks(
        hierarchy.user, TrackListParams(page_size=1, sort="recent")
    )
    assert newest.total_items == 3
    assert newest.data[0].id == javascript.trk_id

    oldest = await service.list_tracks(
        hierarchy.user,
        TrackListParams(page=3, page_size=1, sort="oldest"),
    )
    assert oldest.data[0].id == javascript.trk_id

    beyond = await service.list_tracks(
        hierarchy.user,
        TrackListParams(q="no match", page=5, page_size=1),
    )
    assert beyond.data == []
    assert beyond.total_items == 0
    assert beyond.total_pages == 0


@pytest.mark.anyio
async def test_track_repository_search_escapes_like_wildcards(
    db_session, learning_hierarchy_factory
):
    hierarchy = await learning_hierarchy_factory()
    hierarchy.track.trk_title = "100%_literal"
    await db_session.flush()
    result, total = await TrackRepository(db_session).list(
        hierarchy.user.usr_id, 0, 10, q="100%_literal"
    )
    assert total == 1
    assert result[0].trk_id == hierarchy.track.trk_id


@pytest.mark.anyio
async def test_filtered_track_query_count_is_independent_of_nested_rows(
    db_session, learning_hierarchy_factory, lesson_factory, quiz_factory
):
    hierarchy = await learning_hierarchy_factory()
    for position in range(2, 6):
        lesson = await lesson_factory(hierarchy.step, position=position)
        await quiz_factory(lesson)
    repository = TrackRepository(db_session)
    statements = []

    def collect(_conn, _cursor, statement, *_args):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    connection = await db_session.connection()
    event.listen(connection.sync_connection, "before_cursor_execute", collect)
    try:
        await repository.list(
            hierarchy.user.usr_id,
            0,
            20,
            q="Python",
            level=StepLevelEnum.BEGINNER,
            has_missions=False,
        )
        first_query_count = len(statements)
        for position in range(6, 26):
            lesson = await lesson_factory(hierarchy.step, position=position)
            await quiz_factory(lesson)
        statements.clear()
        await repository.list(
            hierarchy.user.usr_id,
            0,
            100,
            q="Python",
            level=StepLevelEnum.BEGINNER,
            has_missions=False,
        )
    finally:
        event.remove(
            connection.sync_connection, "before_cursor_execute", collect
        )
    assert len(statements) == first_query_count == 9


def test_track_list_params_reject_invalid_filters():
    for payload in (
        {"page": 0},
        {"page_size": 101},
        {"level": "expert"},
        {"has_missions": "maybe"},
        {"sort": "random"},
        {"q": "   "},
        {"owner_id": str(uuid4())},
    ):
        with pytest.raises(ValueError):
            TrackListParams.model_validate(payload)
