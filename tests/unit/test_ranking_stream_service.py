import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from sidebrain_back.schemas.avatar_schema import AvatarResponse
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.ranking_schema import RankingEntryResponse
from sidebrain_back.services import ranking_stream_service
from sidebrain_back.services.ranking_stream_service import (
    RankingStreamService,
    get_ranking_stream_service,
)


def _entry(user_id, xp):
    return RankingEntryResponse(
        position=1, user_id=user_id, name="Aluno", xp=xp, missions_completed=1
    )


@pytest.mark.anyio
async def test_stream_sends_initial_changes_and_heartbeat(monkeypatch):
    user_id = uuid4()
    initial = _entry(user_id, 10)
    updated = _entry(user_id, 20)
    read = AsyncMock(side_effect=[initial, updated, updated, updated])
    request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))
    service = RankingStreamService(None, None)
    monkeypatch.setattr(ranking_stream_service, "MAX_POLLS", 4)
    monkeypatch.setattr(ranking_stream_service, "POLL_INTERVAL_SECONDS", 0)

    events = [
        event async for event in service.stream(request, "xp", initial, read)
    ]

    assert len(events) == 3
    assert events[0].startswith("event: xp\n")
    assert json.loads(events[0].split("data: ")[1])["xp"] == 10
    assert json.loads(events[1].split("data: ")[1])["userId"] == str(user_id)
    assert json.loads(events[1].split("data: ")[1])["xp"] == 20
    assert events[2] == ": keep-alive\n\n"
    assert read.await_count == 4


@pytest.mark.anyio
async def test_stream_sends_avatar_changes_without_xp_change(monkeypatch):
    initial = _entry(uuid4(), 10)
    updated = initial.model_copy(
        update={
            "avatar": AvatarResponse(
                slug="cat",
                name="Gato",
                image_url="/static/avatars/cat.png",
            )
        }
    )
    request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))
    service = RankingStreamService(None, None)
    monkeypatch.setattr(ranking_stream_service, "MAX_POLLS", 1)
    monkeypatch.setattr(ranking_stream_service, "POLL_INTERVAL_SECONDS", 0)

    events = [
        event
        async for event in service.stream(
            request, "xp", initial, AsyncMock(return_value=updated)
        )
    ]

    assert len(events) == 2
    assert json.loads(events[1].split("data: ")[1])["avatar"] == {
        "slug": "cat",
        "name": "Gato",
        "imageUrl": "/static/avatars/cat.png",
    }


@pytest.mark.anyio
async def test_stream_stops_on_disconnect(monkeypatch):
    read = AsyncMock()
    request = SimpleNamespace(is_disconnected=AsyncMock(return_value=True))
    service = RankingStreamService(None, None)
    monkeypatch.setattr(ranking_stream_service, "POLL_INTERVAL_SECONDS", 0)
    events = [
        event
        async for event in service.stream(
            request, "xp", _entry(uuid4(), 10), read
        )
    ]
    assert len(events) == 1
    read.assert_not_awaited()


@pytest.mark.anyio
async def test_reads_release_transaction_even_on_failure():
    db = SimpleNamespace(rollback=AsyncMock())
    ranking = SimpleNamespace(
        list_rankings=AsyncMock(side_effect=RuntimeError("falha"))
    )
    service = RankingStreamService(ranking, db)
    with pytest.raises(RuntimeError):
        await service.list_rankings(1, 20)
    db.rollback.assert_awaited_once()


@pytest.mark.parametrize("path", ["/events", "/me/events"])
def test_stream_requires_authentication(path):
    response = TestClient(app).get(f"/api/v1/rankings{path}")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "path,event", [("/events", "ranking"), ("/me/events", "xp")]
)
def test_stream_endpoint_sends_public_payload(
    test_app, authenticated_user, monkeypatch, path, event
):
    entry = _entry(authenticated_user.usr_id, 100)
    ranking = SimpleNamespace(
        list_rankings=AsyncMock(
            return_value=PaginatedResponse.build(
                [entry], page=1, page_size=20, total_items=1
            )
        ),
        get_my_ranking=AsyncMock(return_value=entry),
    )
    db = SimpleNamespace(rollback=AsyncMock())
    service = RankingStreamService(ranking, db)
    test_app.dependency_overrides[get_ranking_stream_service] = lambda: service
    monkeypatch.setattr(ranking_stream_service, "MAX_POLLS", 0)

    response = TestClient(test_app).get(f"/api/v1/rankings{path}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.startswith(f"event: {event}\ndata: ")
    payload = json.loads(response.text.split("data: ")[1])
    actual = payload["data"][0] if event == "ranking" else payload
    assert actual["xp"] == 100
    assert actual["userId"] == str(authenticated_user.usr_id)
    db.rollback.assert_awaited_once()
