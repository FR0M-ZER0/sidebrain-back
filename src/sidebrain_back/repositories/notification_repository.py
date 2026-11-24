from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.notification_model import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        event_key: str,
        type: str,
        title: str,
        message: str,
        destination: str | None,
    ) -> None:
        self.db.add(
            Notification(
                user_id=user_id,
                event_key=event_key,
                type=type,
                title=title,
                message=message,
                destination=destination,
            )
        )

    async def list_by_user_id(
        self, user_id: UUID, limit: int, offset: int
    ) -> list[Notification]:
        result = await self.db.scalars(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result)

    async def count_unread_by_user_id(self, user_id: UUID) -> int:
        return int(
            await self.db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
            or 0
        )

    async def mark_read_by_user_id(
        self, user_id: UUID, notification_id: UUID
    ) -> bool:
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.id == notification_id,
            )
            .values(
                read_at=func.coalesce(
                    Notification.read_at,
                    datetime.now(UTC).replace(tzinfo=None),
                )
            )
            .returning(Notification.id)
        )
        return result.scalar_one_or_none() is not None


def get_notification_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> NotificationRepository:
    return NotificationRepository(db)
