from uuid import uuid4

import pytest
from fastapi import Request

from sidebrain_back.enums.generation_status_enum import GenerationStatusEnum
from sidebrain_back.routers.v1 import track_router
from sidebrain_back.schemas.generation_schema import GenerationProgress


class ExpiringUser:
    def __init__(self, user_id):
        self.user_id = user_id
        self.read_count = 0

    @property
    def usr_id(self):
        self.read_count += 1
        if self.read_count > 1:
            raise AssertionError("user ORM fields must not be read again")
        return self.user_id


class FakeTrackService:
    def __init__(self, user_id, request_id):
        self.user_id = user_id
        self.request_id = request_id
        self.statuses = [
            GenerationStatusEnum.PENDING,
            GenerationStatusEnum.SUCCEEDED,
        ]

    async def get_generation_progress(self, user_id, request_id):
        assert user_id == self.user_id
        assert request_id == self.request_id
        return GenerationProgress(
            request_id=request_id,
            status=self.statuses.pop(0),
            track_id=(uuid4() if self.statuses == [] else None),
        )


@pytest.mark.anyio
async def test_sse_reuses_captured_user_id_after_orm_user_expires(monkeypatch):
    user_id = uuid4()
    request_id = uuid4()

    async def no_wait(_seconds):
        pass

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    monkeypatch.setattr(track_router.asyncio, "sleep", no_wait)
    request = Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/tracks/generations/events",
            "raw_path": b"/api/v1/tracks/generations/events",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 12345),
        },
        receive,
    )
    user = ExpiringUser(user_id)
    service = FakeTrackService(user_id, request_id)

    response = await track_router.stream_generation_progress(
        request_id, request, user, service
    )
    events = [chunk async for chunk in response.body_iterator]

    assert len(events) == 2
    assert '"status":"pending"' in events[0]
    assert '"status":"succeeded"' in events[1]
    assert user.read_count == 1
