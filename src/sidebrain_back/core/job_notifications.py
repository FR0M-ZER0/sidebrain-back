import asyncio
import logging
from collections import defaultdict

import asyncpg

from sidebrain_back.core.constants import Env

logger = logging.getLogger(__name__)
CHANNEL = "sidebrain_job_updates"


class JobNotificationListener:
    def __init__(self) -> None:
        self._connection: asyncpg.Connection | None = None
        self._subscribers: dict[str, set[asyncio.Event]] = defaultdict(set)
        self._closing = False

    @property
    def available(self) -> bool:
        return (
            self._connection is not None and not self._connection.is_closed()
        )

    async def start(self) -> None:
        if self._connection is not None and not self._connection.is_closed():
            return
        self._closing = False
        self._connection = await asyncpg.connect(
            host=Env.POSTGRES_HOST,
            port=Env.POSTGRES_PORT,
            user=Env.POSTGRES_USER,
            password=Env.POSTGRES_PASSWORD,
            database=Env.POSTGRES_DB,
        )
        await self._connection.add_listener(CHANNEL, self._on_notification)
        self._connection.add_termination_listener(self._on_termination)

    async def close(self) -> None:
        self._closing = True
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
        for events in self._subscribers.values():
            for event in events:
                event.set()
        self._subscribers.clear()

    def _on_termination(self, connection: asyncpg.Connection) -> None:
        if connection is self._connection:
            self._connection = None
        if not self._closing:
            logger.error("job notification listener connection lost")
        for events in self._subscribers.values():
            for event in events:
                event.set()

    def subscribe(self, key: str) -> asyncio.Event:
        event = asyncio.Event()
        self._subscribers[key].add(event)
        return event

    def unsubscribe(self, key: str, event: asyncio.Event) -> None:
        events = self._subscribers.get(key)
        if events is None:
            return
        events.discard(event)
        if not events:
            self._subscribers.pop(key, None)

    def _on_notification(
        self,
        _connection: asyncpg.Connection,
        _pid: int,
        _channel: str,
        payload: str,
    ) -> None:
        for event in tuple(self._subscribers.get(payload, ())):
            event.set()


job_notification_listener = JobNotificationListener()


async def start_job_notification_listener() -> None:
    await job_notification_listener.start()


async def close_job_notification_listener() -> None:
    await job_notification_listener.close()
