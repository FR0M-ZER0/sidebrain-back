import asyncio
import logging

from sidebrain_back.notifications.schemas import NotificationPayload
from sidebrain_back.notifications.worker import run_worker

logger = logging.getLogger(__name__)


class LoggingNotificationHandler:
    async def handle(self, payload: NotificationPayload) -> None:
        logger.info(
            "notification_processed",
            extra={
                "event_id": payload.event_id,
                "type": payload.type,
            },
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker(LoggingNotificationHandler()))
