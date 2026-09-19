from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.step_schema import (
    StepCreate,
    StepResponse,
    StepUpdate,
)
from sidebrain_back.services.step_service import StepService, get_step_service

router = APIRouter(prefix="/v1/tracks/{track_id}/steps", tags=["Steps"])


@router.post(
    "", response_model=StepResponse, status_code=status.HTTP_201_CREATED
)
async def create_step(
    track_id: UUID,
    payload: StepCreate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: StepService = Depends(get_step_service),  # noqa: B008
) -> StepResponse:
    return await service.create_step(user, track_id, payload)


@router.get("", response_model=PaginatedResponse[StepResponse])
async def list_steps(
    track_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
    service: StepService = Depends(get_step_service),  # noqa: B008
) -> PaginatedResponse[StepResponse]:
    return await service.list_steps(user, track_id, page, page_size)


@router.get("/{step_id}", response_model=StepResponse)
async def get_step(
    track_id: UUID,
    step_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: StepService = Depends(get_step_service),  # noqa: B008
) -> StepResponse:
    return await service.get_step(user, track_id, step_id)


@router.put("/{step_id}", response_model=StepResponse)
async def update_step(
    track_id: UUID,
    step_id: UUID,
    payload: StepUpdate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: StepService = Depends(get_step_service),  # noqa: B008
) -> StepResponse:
    return await service.update_step(user, track_id, step_id, payload)


@router.delete("/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    track_id: UUID,
    step_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: StepService = Depends(get_step_service),  # noqa: B008
) -> Response:
    await service.delete_step(user, track_id, step_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
