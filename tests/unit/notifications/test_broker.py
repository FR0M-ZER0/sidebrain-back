import asyncio
from unittest.mock import AsyncMock, MagicMock

from sidebrain_back.core.constants import Env
from sidebrain_back.notifications.broker import (
    build_connection_url,
    declare_topology,
    persistent_message,
)


def test_build_connection_url_encodes_credentials() -> None:
    settings = MagicMock(
        RABBITMQ_USER="user@example",
        RABBITMQ_PASSWORD="p@ss word",
        RABBITMQ_HOST="localhost",
        RABBITMQ_PORT=5672,
        RABBITMQ_VHOST="/",
    )

    assert build_connection_url(settings) == (
        "amqp://user%40example:p%40ss%20word@localhost:5672/%2F"
    )


def test_persistent_message_uses_json_content_type() -> None:
    message = persistent_message(b'{"event_id":"evt-1"}')

    assert message.delivery_mode.name == "PERSISTENT"
    assert message.content_type == "application/json"


def test_declare_topology_is_durable_and_bound() -> None:
    channel = MagicMock()
    exchange = MagicMock()
    dead_letter_exchange = MagicMock()
    queue = MagicMock()
    dead_letter_queue = MagicMock()
    channel.declare_exchange = AsyncMock(
        side_effect=[exchange, dead_letter_exchange]
    )
    channel.declare_queue = AsyncMock(side_effect=[dead_letter_queue, queue])
    dead_letter_queue.bind = AsyncMock()
    queue.bind = AsyncMock()

    topology = asyncio.run(declare_topology(channel, Env))

    assert topology.queue is queue
    channel.declare_exchange.assert_any_await(
        Env.RABBITMQ_EXCHANGE,
        "direct",
        durable=True,
    )
    channel.declare_queue.assert_any_await(Env.RABBITMQ_DLQ, durable=True)
    queue.bind.assert_awaited_once()
