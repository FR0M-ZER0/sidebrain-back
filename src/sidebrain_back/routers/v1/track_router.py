from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.track_schema import (
    TrackCreate,
    TrackResponse,
    TrackUpdate,
)
from sidebrain_back.services.track_service import (
    TrackService,
    get_track_service,
)

router = APIRouter(prefix="/v1/tracks", tags=["Tracks"])


@router.post(
    "", response_model=TrackResponse, status_code=status.HTTP_201_CREATED
)
async def create_track(
    payload: TrackCreate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> TrackResponse:
    return await service.create_track(user, payload)


@router.get("", response_model=PaginatedResponse[TrackResponse])
async def list_tracks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> PaginatedResponse[TrackResponse]:
    return await service.list_tracks(user, page, page_size)


@router.get("/{track_id}", response_model=TrackResponse)
async def get_track(
    track_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> TrackResponse:
    return await service.get_track(user, track_id)


@router.patch("/{track_id}", response_model=TrackResponse)
async def update_track(
    track_id: UUID,
    payload: TrackUpdate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> TrackResponse:
    return await service.update_track(user, track_id, payload)


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(
    track_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> Response:
    await service.delete_track(user, track_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
