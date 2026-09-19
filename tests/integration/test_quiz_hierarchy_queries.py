from math import ceil
from time import perf_counter

import httpx
import pytest
from sqlalchemy import event

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.core.database import engine, get_db

SC005_WARMUP_REQUESTS = 5
SC005_SAMPLE_REQUESTS = 100
SC005_MAX_P95_SECONDS = 2.0


@pytest.mark.anyio
async def test_quiz_list_sc005_latency_and_constant_query_count(
    record_property,
    test_app,
    db_session,
    learning_hierarchy_factory,
    quiz_factory,
    answer_factory,
):
    hierarchy = await learning_hierarchy_factory()

    async def override_db():
        yield db_session

    async def override_user():
        return hierarchy.user

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_current_user] = override_user
    path = (
        f"/api/v1/lessons/{hierarchy.lesson.lsn_id}/quizzes"
        "?page=1&page_size=50"
    )
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        first_quiz = await quiz_factory(hierarchy.lesson)
        for _ in range(10):
            await answer_factory(first_quiz, hierarchy.user)
        query_count_one = await count_statements(client, path)

        for _ in range(49):
            quiz = await quiz_factory(hierarchy.lesson)
            for _ in range(10):
                await answer_factory(quiz, hierarchy.user)
        query_count_fifty = await count_statements(client, path)

        for _ in range(SC005_WARMUP_REQUESTS):
            response = await client.get(path)
            assert response.status_code == 200

        samples = []
        for _ in range(SC005_SAMPLE_REQUESTS):
            started = perf_counter()
            response = await client.get(path)
            samples.append(perf_counter() - started)
            assert response.status_code == 200
            assert len(response.json()["data"]) == 50

    percentile_index = ceil(0.95 * len(samples)) - 1
    p95 = sorted(samples)[percentile_index]
    record_property("sc005_p95_seconds", p95)
    record_property("sc005_query_count_one_quiz", query_count_one)
    record_property("sc005_query_count_fifty_quizzes", query_count_fifty)
    assert p95 <= SC005_MAX_P95_SECONDS
    assert query_count_fifty == query_count_one


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
