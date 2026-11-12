from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractConnection,
    AbstractExchange,
    AbstractQueue,
)

from sidebrain_back.core.constants import Env, _Env


@dataclass
class NotificationTopology:
    exchange: AbstractExchange
    queue: AbstractQueue
    dead_letter_exchange: AbstractExchange
    dead_letter_queue: AbstractQueue


def build_connection_url(settings: _Env = Env) -> str:
    user = quote(settings.RABBITMQ_USER, safe="")
    password = quote(settings.RABBITMQ_PASSWORD, safe="")
    vhost = quote(settings.RABBITMQ_VHOST, safe="")
    return (
        f"amqp://{user}:{password}@{settings.RABBITMQ_HOST}:"
        f"{settings.RABBITMQ_PORT}/{vhost}"
    )


async def declare_topology(
    channel: AbstractChannel,
    settings: _Env = Env,
) -> NotificationTopology:
    exchange = await channel.declare_exchange(
        settings.RABBITMQ_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )
    dead_letter_exchange = await channel.declare_exchange(
        settings.RABBITMQ_DLX,
        ExchangeType.DIRECT,
        durable=True,
    )
    dead_letter_queue = await channel.declare_queue(
        settings.RABBITMQ_DLQ,
        durable=True,
    )
    await dead_letter_queue.bind(
        dead_letter_exchange,
        routing_key=settings.RABBITMQ_ROUTING_KEY,
    )
    queue = await channel.declare_queue(
        settings.RABBITMQ_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": settings.RABBITMQ_DLX,
            "x-dead-letter-routing-key": settings.RABBITMQ_ROUTING_KEY,
        },
    )
    await queue.bind(
        exchange,
        routing_key=settings.RABBITMQ_ROUTING_KEY,
    )
    return NotificationTopology(
        exchange=exchange,
        queue=queue,
        dead_letter_exchange=dead_letter_exchange,
        dead_letter_queue=dead_letter_queue,
    )


async def connect_broker(
    settings: _Env = Env,
) -> tuple[AbstractConnection, AbstractChannel, NotificationTopology]:
    connection = await aio_pika.connect_robust(build_connection_url(settings))
    channel = await connection.channel(publisher_confirms=True)
    topology = await declare_topology(channel, settings)
    return connection, channel, topology


def persistent_message(
    body: bytes,
    headers: dict[str, Any] | None = None,
) -> Message:
    return Message(
        body,
        delivery_mode=DeliveryMode.PERSISTENT,
        content_type="application/json",
        headers=headers or {},
    )
