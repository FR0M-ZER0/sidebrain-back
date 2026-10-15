from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from sidebrain_back.models.user_model import User
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.mission_schema import (
    MissionCreate,
    MissionResponse,
    MissionUpdate,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.services.mission_service import (
    MissionService,
    get_mission_service,
)

router = APIRouter(prefix="/v1", tags=["Missions"])


@router.post(
    "/steps/{step_id}/missions",
    response_model=MissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mission(
    step_id: UUID,
    payload: MissionCreate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MissionService = Depends(get_mission_service),  # noqa: B008
) -> MissionResponse:
    return await service.create_mission(user, step_id, payload)


@router.get(
    "/steps/{step_id}/missions",
    response_model=PaginatedResponse[MissionResponse],
)
async def list_missions(
    step_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
    service: MissionService = Depends(get_mission_service),  # noqa: B008
) -> PaginatedResponse[MissionResponse]:
    return await service.list_missions_by_step_id(
        user, step_id, page, page_size
    )


@router.get("/missions/{mission_id}", response_model=MissionResponse)
async def get_mission(
    mission_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MissionService = Depends(get_mission_service),  # noqa: B008
) -> MissionResponse:
    return await service.get_mission(user, mission_id)


@router.put("/missions/{mission_id}", response_model=MissionResponse)
async def update_mission(
    mission_id: UUID,
    payload: MissionUpdate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MissionService = Depends(get_mission_service),  # noqa: B008
) -> MissionResponse:
    return await service.update_mission(user, mission_id, payload)


@router.delete(
    "/missions/{mission_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_mission(
    mission_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MissionService = Depends(get_mission_service),  # noqa: B008
) -> Response:
    await service.delete_mission(user, mission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
