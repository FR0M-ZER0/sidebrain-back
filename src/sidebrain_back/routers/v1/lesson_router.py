from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.lesson_schema import (
    LessonCreateRequest,
    LessonResponse,
    LessonUpdateRequest,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.services.lesson_service import (
    LessonService,
    get_lesson_service,
)

router = APIRouter(prefix="/v1", tags=["Lessons"])


@router.post(
    "/steps/{step_id}/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson(
    step_id: UUID,
    payload: LessonCreateRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: LessonService = Depends(get_lesson_service),  # noqa: B008
) -> LessonResponse:
    return await service.create_lesson(user, step_id, payload)


@router.get(
    "/steps/{step_id}/lessons",
    response_model=PaginatedResponse[LessonResponse],
)
async def list_lessons_by_step_id(
    step_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
    service: LessonService = Depends(get_lesson_service),  # noqa: B008
) -> PaginatedResponse[LessonResponse]:
    return await service.list_lessons_by_step_id(
        user,
        step_id,
        page,
        page_size,
    )


@router.get("/lessons/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: LessonService = Depends(get_lesson_service),  # noqa: B008
) -> LessonResponse:
    return await service.get_lesson(user, lesson_id)


@router.put("/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: UUID,
    payload: LessonUpdateRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: LessonService = Depends(get_lesson_service),  # noqa: B008
) -> LessonResponse:
    return await service.update_lesson(user, lesson_id, payload)


@router.delete(
    "/lessons/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_lesson(
    lesson_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: LessonService = Depends(get_lesson_service),  # noqa: B008
) -> Response:
    await service.delete_lesson(user, lesson_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
