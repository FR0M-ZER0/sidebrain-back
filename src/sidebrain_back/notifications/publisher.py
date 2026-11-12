import json
import logging
from datetime import UTC, datetime

from aio_pika.abc import AbstractExchange

from sidebrain_back.core.constants import Env, _Env
from sidebrain_back.notifications.broker import persistent_message
from sidebrain_back.notifications.schemas import NotificationPayload

logger = logging.getLogger(__name__)


class NotificationPublisher:
    def __init__(
        self,
        exchange: AbstractExchange,
        settings: _Env = Env,
    ) -> None:
        self._exchange = exchange
        self._settings = settings

    async def publish(self, payload: NotificationPayload) -> None:
        if not isinstance(payload, NotificationPayload):
            raise TypeError("payload deve ser um NotificationPayload")

        try:
            body = json.dumps(
                payload.model_dump(),
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            await self._exchange.publish(
                persistent_message(body),
                routing_key=self._settings.RABBITMQ_ROUTING_KEY,
                mandatory=True,
            )
        except Exception as error:
            logger.error(
                "notification_publish_failed",
                extra={
                    "event_id": payload.event_id,
                    "type": payload.type,
                    "attempt": 1,
                    "error": str(error),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
            raise
