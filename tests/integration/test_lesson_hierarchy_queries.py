from math import ceil
from time import perf_counter

import httpx
import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.core.database import engine, get_db

SC007_WARMUP_REQUESTS = 5
SC007_SAMPLE_REQUESTS = 100
SC007_MAX_P95_SECONDS = 2.0


@pytest.mark.anyio
async def test_lesson_list_sc007_latency_and_sc008_constant_query_count(
    record_property,
    test_app,
    db_session,
    learning_hierarchy_factory,
    lesson_factory,
    feedback_factory,
    lesson_file_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()

    async def override_db():
        async with AsyncSession(
            bind=db_session.bind,
            expire_on_commit=False,
        ) as request_session:
            yield request_session

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides.pop(get_current_user, None)
    path = f"/api/v1/steps/{hierarchy.step.stp_id}/lessons?page=1&page_size=50"
    headers = {"Authorization": f"Bearer {hierarchy.user.usr_id}"}
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers=headers,
    ) as client:
        await create_children(
            hierarchy.lesson,
            hierarchy.user,
            feedback_factory,
            lesson_file_factory,
            quiz_factory,
            answer_factory,
        )
        await db_session.flush()
        query_count_one = await count_statements(client, path)

        for position in range(2, 51):
            lesson = await lesson_factory(
                hierarchy.step, position=position, flush=False
            )
            await create_children(
                lesson,
                hierarchy.user,
                feedback_factory,
                lesson_file_factory,
                quiz_factory,
                answer_factory,
            )
        await db_session.flush()
        query_count_fifty = await count_statements(client, path)

        response = await client.get(path)
        assert response.status_code == 200
        assert_complete_dataset(response.json())

        for _ in range(SC007_WARMUP_REQUESTS):
            response = await client.get(path)
            assert response.status_code == 200

        samples = []
        for _ in range(SC007_SAMPLE_REQUESTS):
            started = perf_counter()
            response = await client.get(path)
            samples.append(perf_counter() - started)
            assert response.status_code == 200
            assert len(response.json()["data"]) == 50

    percentile_index = ceil(0.95 * len(samples)) - 1
    p95 = sorted(samples)[percentile_index]
    record_property("sc007_p95_seconds", p95)
    record_property("sc008_query_count_one_lesson", query_count_one)
    record_property("sc008_query_count_fifty_lessons", query_count_fifty)
    assert p95 <= SC007_MAX_P95_SECONDS
    assert query_count_one > 0
    assert query_count_fifty == query_count_one


async def create_children(
    lesson,
    user,
    feedback_factory,
    lesson_file_factory,
    quiz_factory,
    answer_factory,
):
    for _ in range(5):
        await feedback_factory(lesson, user, flush=False)
    for _ in range(3):
        await lesson_file_factory(lesson, flush=False)
    for _ in range(5):
        quiz = await quiz_factory(lesson, flush=False)
        for _ in range(10):
            await answer_factory(quiz, user, flush=False)


def assert_complete_dataset(body):
    assert len(body["data"]) == 50
    for lesson in body["data"]:
        assert len(lesson["feedbacks"]) == 5
        assert len(lesson["files"]) == 3
        assert len(lesson["quizzes"]) == 5
        assert all(len(quiz["answers"]) == 10 for quiz in lesson["quizzes"])


async def count_statements(client: httpx.AsyncClient, path: str) -> int:
    statements = 0

    def increment(*_args):
        nonlocal statements
        statements += 1

    event.listen(engine.sync_engine, "before_cursor_execute", increment)
    try:
        response = await client.get(path)
        assert response.status_code == 200
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", increment)
    return statements
