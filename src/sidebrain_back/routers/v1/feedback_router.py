from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.feedback_schema import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.services.feedback_service import (
    FeedbackService,
    get_feedback_service,
)

router = APIRouter(tags=["Feedbacks"])


@router.post(
    "/v1/lessons/{lesson_id}/feedbacks",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feedback(
    lesson_id: UUID,
    payload: FeedbackCreate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: FeedbackService = Depends(get_feedback_service),  # noqa: B008
) -> FeedbackResponse:
    return await service.create_feedback(user, lesson_id, payload)


@router.get(
    "/v1/lessons/{lesson_id}/feedbacks",
    response_model=PaginatedResponse[FeedbackResponse],
)
async def list_feedbacks(
    lesson_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _user: User = Depends(get_current_user),  # noqa: B008
    service: FeedbackService = Depends(get_feedback_service),  # noqa: B008
) -> PaginatedResponse[FeedbackResponse]:
    return await service.list_feedbacks_by_lesson(lesson_id, page, page_size)


@router.get("/v1/feedbacks/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: UUID,
    _user: User = Depends(get_current_user),  # noqa: B008
    service: FeedbackService = Depends(get_feedback_service),  # noqa: B008
) -> FeedbackResponse:
    return await service.get_feedback(feedback_id)


@router.patch("/v1/feedbacks/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: UUID,
    payload: FeedbackUpdate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: FeedbackService = Depends(get_feedback_service),  # noqa: B008
) -> FeedbackResponse:
    return await service.update_feedback(user, feedback_id, payload)


@router.delete(
    "/v1/feedbacks/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_feedback(
    feedback_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: FeedbackService = Depends(get_feedback_service),  # noqa: B008
) -> Response:
    await service.delete_feedback(user, feedback_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
