import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

from aio_pika.abc import AbstractExchange, AbstractIncomingMessage
from pydantic import ValidationError

from sidebrain_back.core.constants import Env, _Env
from sidebrain_back.notifications.broker import persistent_message
from sidebrain_back.notifications.handler import (
    NotificationHandler,
    PermanentNotificationError,
)
from sidebrain_back.notifications.schemas import NotificationPayload

logger = logging.getLogger(__name__)


class NotificationConsumer:
    def __init__(
        self,
        exchange: AbstractExchange,
        handler: NotificationHandler,
        settings: _Env = Env,
        *,
        max_attempts: int | None = None,
        retry_delay_seconds: float | None = None,
        backoff_factor: float | None = None,
    ) -> None:
        self._exchange = exchange
        self._handler = handler
        self._settings = settings
        self._max_attempts = max_attempts or settings.RABBITMQ_MAX_ATTEMPTS
        self._retry_delay_seconds = (
            retry_delay_seconds
            if retry_delay_seconds is not None
            else settings.RABBITMQ_RETRY_DELAY_SECONDS
        )
        self._backoff_factor = (
            backoff_factor
            if backoff_factor is not None
            else settings.RABBITMQ_BACKOFF_FACTOR
        )

    async def process_message(
        self,
        message: AbstractIncomingMessage,
    ) -> None:
        raw_payload: dict[str, Any] = {}
        try:
            raw_payload = json.loads(message.body)
            payload = NotificationPayload.model_validate(raw_payload)
        except (
            TypeError,
            ValueError,
            ValidationError,
            json.JSONDecodeError,
        ) as error:
            self._log("notification_validation_failed", raw_payload, 1, error)
            await message.reject(requeue=False)
            return

        attempt = int((message.headers or {}).get("x-attempt", 1))
        try:
            await self._handler.handle(payload)
        except PermanentNotificationError as error:
            self._log(
                "notification_failed_permanently",
                raw_payload,
                attempt,
                error,
            )
            await message.reject(requeue=False)
        except Exception as error:
            if attempt >= self._max_attempts:
                self._log(
                    "notification_failed_permanently",
                    raw_payload,
                    attempt,
                    error,
                )
                await message.reject(requeue=False)
                return

            delay = self._retry_delay_seconds * (
                self._backoff_factor ** (attempt - 1)
            )
            self._log(
                "notification_retry_scheduled",
                raw_payload,
                attempt,
                error,
            )
            await asyncio.sleep(delay)
            await self._exchange.publish(
                persistent_message(
                    message.body,
                    headers={
                        **(message.headers or {}),
                        "x-attempt": attempt + 1,
                    },
                ),
                routing_key=self._settings.RABBITMQ_ROUTING_KEY,
                mandatory=True,
            )
            await message.ack()
        else:
            await message.ack()

    async def consume(self, queue: Any) -> None:
        await queue.consume(self.process_message)

    def _log(
        self,
        event: str,
        raw_payload: dict[str, Any],
        attempt: int,
        error: Exception,
    ) -> None:
        logger.error(
            event,
            extra={
                "event_id": raw_payload.get("event_id"),
                "type": raw_payload.get("type"),
                "attempt": attempt,
                "error": str(error),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
