import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from sidebrain_back.notifications.publisher import NotificationPublisher
from sidebrain_back.notifications.schemas import NotificationPayload


def _payload() -> NotificationPayload:
    return NotificationPayload(
        event_id="evt-1",
        type="lesson.completed",
        data={"lesson_id": "lesson-1"},
    )


def test_publisher_sends_persistent_json_message() -> None:
    exchange = MagicMock()
    exchange.publish = AsyncMock()
    publisher = NotificationPublisher(exchange)

    asyncio.run(publisher.publish(_payload()))

    message = exchange.publish.await_args.args[0]
    assert json.loads(message.body) == _payload().model_dump()
    assert message.delivery_mode.name == "PERSISTENT"
    assert exchange.publish.await_args.kwargs == {
        "routing_key": "notification",
        "mandatory": True,
    }


def test_publisher_rejects_invalid_payload_before_broker_call() -> None:
    with pytest.raises(ValidationError):
        NotificationPayload(event_id="", type="event", data={})

    exchange = MagicMock()
    exchange.publish = AsyncMock()
    publisher = NotificationPublisher(exchange)

    with pytest.raises(TypeError):
        asyncio.run(publisher.publish({"event_id": "evt"}))

    exchange.publish.assert_not_awaited()


def test_publisher_logs_broker_failure_without_payload(caplog) -> None:
    exchange = MagicMock()
    exchange.publish = AsyncMock(
        side_effect=RuntimeError("broker unavailable")
    )
    publisher = NotificationPublisher(exchange)

    with pytest.raises(RuntimeError):
        asyncio.run(publisher.publish(_payload()))

    record = caplog.records[-1]
    assert record.event_id == "evt-1"
    assert record.type == "lesson.completed"
    assert "lesson_id" not in caplog.text
