import asyncio
from unittest.mock import AsyncMock, MagicMock

from sidebrain_back.notifications.publisher import NotificationPublisher
from sidebrain_back.notifications.schemas import NotificationPayload


def test_publisher_contract_uses_notification_routing() -> None:
    exchange = MagicMock()
    exchange.publish = AsyncMock()
    publisher = NotificationPublisher(exchange)

    asyncio.run(
        publisher.publish(
            NotificationPayload(
                event_id="evt-contract",
                type="notification.created",
                data={"safe": True},
            )
        )
    )

    assert exchange.publish.await_args.kwargs["routing_key"] == "notification"
    assert exchange.publish.await_args.kwargs["mandatory"] is True
