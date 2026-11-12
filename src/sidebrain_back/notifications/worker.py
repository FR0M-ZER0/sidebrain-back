import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sidebrain_back.notifications.broker import connect_broker
from sidebrain_back.notifications.consumer import NotificationConsumer
from sidebrain_back.notifications.handler import NotificationHandler

logger = logging.getLogger(__name__)


async def run_worker(handler: NotificationHandler) -> None:
    connection, _channel, topology = await connect_broker()
    consumer = NotificationConsumer(topology.exchange, handler)
    try:
        await consumer.consume(topology.queue)
        await asyncio.Future()
    finally:
        await connection.close()


class CallbackNotificationHandler:
    def __init__(
        self,
        callback: Callable[[Any], Awaitable[Any]],
    ) -> None:
        self._callback = callback

    async def handle(self, payload: Any) -> Any:
        return await self._callback(payload)
