from fastapi import APIRouter, Depends

from sidebrain_back.models.user_model import User
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.avatar_schema import AvatarListResponse
from sidebrain_back.services.avatar_service import (
    AvatarService,
    get_avatar_service,
)

router = APIRouter(prefix="/v1", tags=["Avatars"])


@router.get("/avatars", response_model=AvatarListResponse)
async def list_avatars(
    _user: User = Depends(get_current_user),  # noqa: B008
    service: AvatarService = Depends(get_avatar_service),  # noqa: B008
) -> AvatarListResponse:
    return await service.list_active()
