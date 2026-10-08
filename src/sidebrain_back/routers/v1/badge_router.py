from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.badge_schema import (
    BadgeCreate,
    BadgeResponse,
    BadgeUpdate,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.services.badge_service import (
    BadgeService,
    get_badge_service,
)

router = APIRouter(prefix="/v1", tags=["Badges"])


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
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
    service: BadgeService = Depends(get_badge_service),  # noqa: B008
) -> PaginatedResponse[BadgeResponse]:
    return await service.list_badges(user, page, page_size)


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
