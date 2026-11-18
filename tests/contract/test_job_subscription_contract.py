from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from main import app
from sidebrain_back.core.ws_tickets import get_ws_ticket_store
from sidebrain_back.routers.v1 import job_update_router
from sidebrain_back.schemas.job_update_schema import (
    JobUpdated,
    TrackGenerationPayload,
)


class FakeTicketStore:
    def __init__(self, scope):
        self.scope = scope

    async def consume(self, _ticket):
        return dict(self.scope)


@pytest.fixture
def websocket_scope():
    request_id = uuid4()
    return request_id, {
        "user_id": str(uuid4()),
        "channel": "track_generation",
        "resource_id": str(request_id),
    }


def test_websocket_delivers_terminal_snapshot(monkeypatch, websocket_scope):
    request_id, raw_scope = websocket_scope
    snapshot = JobUpdated(
        channel="track_generation",
        resource_id=str(request_id),
        payload=TrackGenerationPayload(
            request_id=request_id,
            status="succeeded",
            track_id=uuid4(),
        ),
    )

    async def load_snapshot(_user_id, _scope):
        return snapshot

    monkeypatch.setattr(job_update_router, "load_job_snapshot", load_snapshot)
    app.dependency_overrides[get_ws_ticket_store] = lambda: FakeTicketStore(
        raw_scope
    )
    try:
        with TestClient(app) as client:
            with client.websocket_connect(
                "/api/v1/ws?ticket=temporary"
            ) as websocket:
                websocket.send_json(
                    {
                        "type": "subscribe",
                        "channel": "track_generation",
                        "resource_id": str(request_id),
                    }
                )
                assert websocket.receive_json() == snapshot.model_dump(
                    mode="json"
                )
                with pytest.raises(WebSocketDisconnect) as closed:
                    websocket.receive_json()
                assert closed.value.code == 1000
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("binary", [False, True])
def test_websocket_rejects_invalid_subscription_using_authorized_scope(
    binary, websocket_scope
):
    request_id, raw_scope = websocket_scope
    app.dependency_overrides[get_ws_ticket_store] = lambda: FakeTicketStore(
        raw_scope
    )
    try:
        with TestClient(app) as client:
            with client.websocket_connect(
                "/api/v1/ws?ticket=temporary"
            ) as websocket:
                if binary:
                    websocket.send_bytes(b"not-json")
                else:
                    websocket.send_json(
                        {
                            "type": "subscribe",
                            "channel": "track_generation",
                            "resource_id": str(uuid4()),
                        }
                    )
                error = websocket.receive_json()
                assert error["type"] == "job.error"
                assert error["channel"] == "track_generation"
                assert error["resource_id"] == str(request_id)
                with pytest.raises(WebSocketDisconnect) as closed:
                    websocket.receive_json()
                assert closed.value.code == 1008
    finally:
        app.dependency_overrides.clear()
