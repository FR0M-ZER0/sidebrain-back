import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from sidebrain_back.notifications.consumer import NotificationConsumer
from sidebrain_back.notifications.handler import NotificationHandler


class FakeMessage:
    def __init__(self, payload: dict, headers: dict | None = None) -> None:
        self.body = json.dumps(payload).encode()
        self.headers = headers or {}
        self.ack = AsyncMock()
        self.reject = AsyncMock()


def _payload() -> dict:
    return {
        "event_id": "evt-1",
        "type": "lesson.completed",
        "data": {"lesson_id": "lesson-1"},
    }


def test_success_acks_only_after_handler() -> None:
    handler = AsyncMock(spec=NotificationHandler)
    exchange = MagicMock()
    consumer = NotificationConsumer(exchange, handler)
    message = FakeMessage(_payload())

    asyncio.run(consumer.process_message(message))

    handler.handle.assert_awaited_once()
    message.ack.assert_awaited_once()
    message.reject.assert_not_awaited()


def test_invalid_message_is_sent_to_dlq_without_retry() -> None:
    handler = AsyncMock(spec=NotificationHandler)
    exchange = MagicMock()
    consumer = NotificationConsumer(exchange, handler)
    message = FakeMessage({"event_id": "evt-1", "type": "invalid"})

    asyncio.run(consumer.process_message(message))

    handler.handle.assert_not_awaited()
    message.reject.assert_awaited_once_with(requeue=False)
    exchange.publish.assert_not_called()


def test_failure_does_not_prevent_next_message() -> None:
    handler = AsyncMock(spec=NotificationHandler)
    handler.handle.side_effect = [RuntimeError("temporary"), None]
    exchange = MagicMock()
    exchange.publish = AsyncMock()
    consumer = NotificationConsumer(
        exchange,
        handler,
        retry_delay_seconds=0,
    )
    first = FakeMessage(_payload())
    second = FakeMessage({**_payload(), "event_id": "evt-2"})

    asyncio.run(consumer.process_message(first))
    asyncio.run(consumer.process_message(second))

    assert handler.handle.await_count == 2
    first.ack.assert_awaited_once()
    second.ack.assert_awaited_once()
