from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from sidebrain_back.models.user_model import User
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.notification_schema import NotificationListResponse
from sidebrain_back.services.notification_service import (
    NotificationService,
    get_notification_service,
)

router = APIRouter(prefix="/v1/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),  # noqa: B008
    service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> NotificationListResponse:
    return await service.list_by_user_id(user.usr_id, limit, offset)


@router.patch("/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> Response:
    await service.mark_read_by_user_id(user.usr_id, notification_id)
    return Response(status_code=204)
