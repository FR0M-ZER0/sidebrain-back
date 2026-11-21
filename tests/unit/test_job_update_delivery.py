import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.routers.v1 import job_update_router


@pytest.mark.anyio
@pytest.mark.parametrize(
    "channel",
    ["track_generation", "assessment", "step_preparation", "step_summary"],
)
@pytest.mark.parametrize("after_update", [False, True])
async def test_revocation_before_delivery_only_sends_generic_error(
    monkeypatch, channel, after_update
):
    resource_id = str(uuid4())
    if channel == "step_summary":
        resource_id += f":{uuid4()}"
    raw_scope = {
        "user_id": str(uuid4()),
        "channel": channel,
        "resource_id": resource_id,
    }
    pending = SimpleNamespace(
        model_dump_json=lambda: '{"status":"pending"}',
        payload=SimpleNamespace(status="pending"),
    )
    terminal = SimpleNamespace(
        model_dump_json=lambda: '{"status":"completed"}',
        payload=SimpleNamespace(status="completed"),
    )
    revoked = ProblemDetailError(404, "Não encontrado", "private reason")
    snapshots = (
        [pending, pending, terminal, revoked]
        if after_update
        else [terminal, revoked]
    )
    load = AsyncMock(side_effect=snapshots)
    monkeypatch.setattr(job_update_router, "load_job_snapshot", load)
    listener = SimpleNamespace(
        available=True,
        start=AsyncMock(),
        subscribe=Mock(return_value=asyncio.Event()),
        unsubscribe=Mock(),
    )
    monkeypatch.setattr(
        job_update_router, "job_notification_listener", listener
    )
    websocket = SimpleNamespace(
        accept=AsyncMock(),
        receive=AsyncMock(
            return_value={
                "type": "websocket.receive",
                "text": (
                    '{"type":"subscribe","channel":"'
                    + channel
                    + '","resource_id":"'
                    + resource_id
                    + '"}'
                ),
            }
        ),
        send_text=AsyncMock(),
        send_json=AsyncMock(),
        close=AsyncMock(),
    )
    await job_update_router.job_updates(
        websocket,
        "ticket",
        SimpleNamespace(consume=AsyncMock(return_value=raw_scope)),
    )
    if after_update:
        websocket.send_text.assert_awaited_once_with(pending.model_dump_json())
    else:
        websocket.send_text.assert_not_awaited()
    websocket.send_json.assert_awaited_once_with(
        {
            "type": "job.error",
            "channel": channel,
            "resource_id": resource_id,
            "message": "Recurso indisponível.",
        }
    )
    websocket.close.assert_awaited_once_with(code=1008)
    listener.unsubscribe.assert_called_once()
