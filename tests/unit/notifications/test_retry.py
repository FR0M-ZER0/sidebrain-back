import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from sidebrain_back.notifications.consumer import NotificationConsumer
from sidebrain_back.notifications.handler import NotificationHandler

from .test_consumer import FakeMessage, _payload


def test_transient_failure_republishes_with_incremented_attempt() -> None:
    handler = AsyncMock(spec=NotificationHandler)
    handler.handle.side_effect = RuntimeError("temporary")
    exchange = MagicMock()
    exchange.publish = AsyncMock()
    consumer = NotificationConsumer(
        exchange,
        handler,
        max_attempts=5,
        retry_delay_seconds=2,
        backoff_factor=2,
    )
    message = FakeMessage(_payload(), {"x-attempt": 2})

    with patch(
        "sidebrain_back.notifications.consumer.asyncio.sleep",
        new=AsyncMock(),
    ) as sleep:
        asyncio.run(consumer.process_message(message))

    sleep.assert_awaited_once_with(4)
    assert exchange.publish.await_count == 1
    assert exchange.publish.await_args.kwargs["routing_key"] == "notification"
    assert exchange.publish.await_args.args[0].headers["x-attempt"] == 3
    message.ack.assert_awaited_once()


def test_fifth_failure_is_rejected_to_dead_letter_queue() -> None:
    handler = AsyncMock(spec=NotificationHandler)
    handler.handle.side_effect = RuntimeError("permanent")
    exchange = MagicMock()
    exchange.publish = AsyncMock()
    consumer = NotificationConsumer(exchange, handler, max_attempts=5)
    message = FakeMessage(_payload(), {"x-attempt": 5})

    asyncio.run(consumer.process_message(message))

    message.reject.assert_awaited_once_with(requeue=False)
    message.ack.assert_not_awaited()
    exchange.publish.assert_not_called()
