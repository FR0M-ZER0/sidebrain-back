from fastapi import APIRouter, Depends

from sidebrain_back.models.user_model import User
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.user_statistics_schema import (
    UserStatisticsResponse,
)
from sidebrain_back.services.user_statistics_service import (
    UserStatisticsService,
    get_user_statistics_service,
)

router = APIRouter(prefix="/v1/users", tags=["Users"])


@router.get("/me/statistics", response_model=UserStatisticsResponse)
async def get_user_statistics(
    user: User = Depends(get_current_user),  # noqa: B008
    service: UserStatisticsService = Depends(  # noqa: B008
        get_user_statistics_service
    ),
) -> UserStatisticsResponse:
    return await service.get_user_statistics(user)
