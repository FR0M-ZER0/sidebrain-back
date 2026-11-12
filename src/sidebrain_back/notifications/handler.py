from typing import Any, Protocol

from sidebrain_back.notifications.schemas import NotificationPayload


class TransientNotificationError(Exception):
    """A notification can be processed again later."""


class PermanentNotificationError(Exception):
    """A notification must be isolated without another retry."""


class NotificationHandler(Protocol):
    async def handle(
        self,
        payload: NotificationPayload,
    ) -> Any: ...
