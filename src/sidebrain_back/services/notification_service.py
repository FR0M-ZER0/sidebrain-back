from uuid import UUID

from fastapi import Depends

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.repositories.notification_repository import (
    NotificationRepository,
    get_notification_repository,
)
from sidebrain_back.schemas.notification_schema import (
    NotificationListResponse,
    NotificationResponse,
)


class NotificationService:
    def __init__(self, repository: NotificationRepository) -> None:
        self.repository = repository

    async def list_by_user_id(
        self, user_id: UUID, limit: int, offset: int
    ) -> NotificationListResponse:
        items = await self.repository.list_by_user_id(user_id, limit, offset)
        count = await self.repository.count_unread_by_user_id(user_id)
        return NotificationListResponse(
            items=[
                NotificationResponse.model_validate(item) for item in items
            ],
            unread_count=count,
        )

    async def mark_read_by_user_id(
        self, user_id: UUID, notification_id: UUID
    ) -> None:
        if not await self.repository.mark_read_by_user_id(
            user_id, notification_id
        ):
            raise ProblemDetailError(
                404, "Não encontrado", "Notificação não encontrada."
            )
        await self.repository.db.commit()


def get_notification_service(
    repository: NotificationRepository = Depends(  # noqa: B008
        get_notification_repository
    ),
) -> NotificationService:
    return NotificationService(repository)
