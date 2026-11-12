import asyncio
import os

import pytest

from sidebrain_back.notifications.broker import connect_broker
from sidebrain_back.notifications.consumer import NotificationConsumer
from sidebrain_back.notifications.publisher import NotificationPublisher
from sidebrain_back.notifications.schemas import NotificationPayload


def test_rabbitmq_topology_is_available_when_enabled() -> None:
    if os.getenv("RUN_RABBITMQ_TESTS") != "1":
        pytest.skip("defina RUN_RABBITMQ_TESTS=1 para usar RabbitMQ local")

    async def verify() -> None:
        connection, channel, topology = await connect_broker()
        try:
            await topology.queue.purge()
            await topology.dead_letter_queue.purge()
            assert topology.queue.name
            assert topology.dead_letter_queue.name
            assert channel.is_closed is False

            publisher = NotificationPublisher(topology.exchange)
            await publisher.publish(
                NotificationPayload(
                    event_id="integration-event",
                    type="integration.test",
                    data={"ok": True},
                )
            )
            message = await topology.queue.get(timeout=2)
            assert message is not None
            assert b"integration-event" in message.body
            await message.ack()

            class FailingHandler:
                async def handle(self, payload: NotificationPayload) -> None:
                    raise RuntimeError("integration failure")

            await publisher.publish(
                NotificationPayload(
                    event_id="integration-dead-letter",
                    type="integration.test",
                    data={"ok": False},
                )
            )
            message = await topology.queue.get(timeout=2)
            assert message is not None
            consumer = NotificationConsumer(
                topology.exchange,
                FailingHandler(),
                max_attempts=1,
            )
            await consumer.process_message(message)
            dead_lettered = await topology.dead_letter_queue.get(timeout=2)
            assert dead_lettered is not None
            assert b"integration-dead-letter" in dead_lettered.body
            await dead_lettered.ack()
        finally:
            await connection.close()

    asyncio.run(verify())
