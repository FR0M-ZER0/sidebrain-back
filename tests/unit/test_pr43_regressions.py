import asyncio
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from sidebrain_back.core.job_notifications import JobNotificationListener
from sidebrain_back.schemas.job_update_schema import JobScope
from sidebrain_back.services.track_service import TrackService


@pytest.mark.anyio
async def test_listener_serializes_concurrent_starts(monkeypatch):
    module = import_module("sidebrain_back.core.job_notifications")
    calls = []

    class Connection:
        def is_closed(self):
            return False

        async def add_listener(self, *_args):
            await asyncio.sleep(0)

        def add_termination_listener(self, _callback):
            pass

        async def close(self):
            calls.append("closed")

    async def connect(**_kwargs):
        calls.append("connected")
        await asyncio.sleep(0)
        return Connection()

    monkeypatch.setattr(module.asyncpg, "connect", connect)
    listener = JobNotificationListener()
    await asyncio.gather(listener.start(), listener.start())
    await listener.close()
    assert calls == ["connected", "closed"]


@pytest.mark.parametrize("channel", ["assessment", "track_generation"])
def test_scope_canonicalizes_uppercase_and_unhyphenated_uuid(channel):
    resource = uuid4()
    assert JobScope(
        channel=channel, resource_id=resource.hex.upper()
    ).resource_id == str(resource)


def test_summary_scope_canonicalizes_both_uuids():
    track, step = uuid4(), uuid4()
    assert (
        JobScope(
            channel="step_summary",
            resource_id=f"{track.hex.upper()}:{str(step).upper()}",
        ).resource_id
        == f"{track}:{step}"
    )


def test_ambiguous_dispatch_retries_same_identity():
    task = SimpleNamespace(
        apply_async=Mock(
            side_effect=[TimeoutError(), SimpleNamespace(id="reserved")]
        )
    )
    result = TrackService._dispatch_preparation(task, uuid4(), "reserved")
    assert result.id == "reserved"
    assert (
        task.apply_async.call_args_list[0]
        == (task.apply_async.call_args_list[1])
    )


@pytest.mark.parametrize(
    "reason, terminal",
    [
        ("content_already_exists", "completed"),
        ("step_not_found_or_inactive", "failed"),
    ],
)
def test_worker_distinguishes_skipped_results(monkeypatch, reason, terminal):
    module = import_module(
        "sidebrain_back.tasks.prepare_next_step_content_task"
    )
    transitions = []

    async def prepare(_step):
        return {"status": "skipped", "reason": reason}

    async def dispose():
        pass

    async def finish(task_id, status):
        transitions.append((task_id, status))

    monkeypatch.setattr(module, "_prepare_step_content", prepare)
    monkeypatch.setattr(module, "_finish_preparation", finish)
    monkeypatch.setattr(module, "engine", SimpleNamespace(dispose=dispose))
    module.prepare_next_step_content_task.run(str(uuid4()), "reserved")
    assert transitions == [("reserved", terminal)]
