from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from sidebrain_back.models.user_model import User
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.badge_schema import (
    BadgeCreate,
    BadgeListParams,
    BadgeResponse,
    BadgeUpdate,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.services.badge_progress_service import (
    BadgeProgressService,
    get_badge_progress_service,
)
from sidebrain_back.services.badge_service import (
    BadgeService,
    get_badge_service,
)

router = APIRouter(prefix="/v1", tags=["Badges"])


@router.post(
    "/badges/recalculate-progress",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def recalculate_badge_progress(
    user: User = Depends(get_current_user),  # noqa: B008
    service: BadgeProgressService = Depends(  # noqa: B008
        get_badge_progress_service
    ),
) -> Response:
    await service.recalculate_badges_by_user_id(user.usr_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/badges",
    response_model=BadgeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_badge(
    payload: BadgeCreate,
    _user: User = Depends(get_current_user),  # noqa: B008
    service: BadgeService = Depends(get_badge_service),  # noqa: B008
) -> BadgeResponse:
    return await service.create_badge(_user, payload)


@router.get("/badges", response_model=PaginatedResponse[BadgeResponse])
async def list_badges(
    params: Annotated[BadgeListParams, Query()],
    user: User = Depends(get_current_user),  # noqa: B008
    service: BadgeService = Depends(get_badge_service),  # noqa: B008
) -> PaginatedResponse[BadgeResponse]:
    return await service.list_badges(user, params)


@router.get("/badges/{badge_id}", response_model=BadgeResponse)
async def get_badge(
    badge_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: BadgeService = Depends(get_badge_service),  # noqa: B008
) -> BadgeResponse:
    return await service.get_badge(user, badge_id)


@router.patch("/badges/{badge_id}", response_model=BadgeResponse)
async def update_badge(
    badge_id: UUID,
    payload: BadgeUpdate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: BadgeService = Depends(get_badge_service),  # noqa: B008
) -> BadgeResponse:
    return await service.update_badge(user, badge_id, payload)


@router.delete("/badges/{badge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_badge(
    badge_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: BadgeService = Depends(get_badge_service),  # noqa: B008
) -> Response:
    await service.delete_badge(user, badge_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
