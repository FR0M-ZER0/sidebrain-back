from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.quiz_schema import (
    QuizCreateRequest,
    QuizResponse,
    QuizUpdateRequest,
)
from sidebrain_back.services.quiz_service import QuizService, get_quiz_service

router = APIRouter(prefix="/v1", tags=["Quizzes"])


@router.post(
    "/lessons/{lesson_id}/quizzes",
    response_model=QuizResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_quiz(
    lesson_id: UUID,
    payload: QuizCreateRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: QuizService = Depends(get_quiz_service),  # noqa: B008
) -> QuizResponse:
    return await service.create_quiz(user, lesson_id, payload)


@router.get(
    "/lessons/{lesson_id}/quizzes",
    response_model=PaginatedResponse[QuizResponse],
)
async def list_quizzes_by_lesson(
    lesson_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
    service: QuizService = Depends(get_quiz_service),  # noqa: B008
) -> PaginatedResponse[QuizResponse]:
    return await service.list_quizzes_by_lesson(
        user,
        lesson_id,
        page,
        page_size,
    )


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: QuizService = Depends(get_quiz_service),  # noqa: B008
) -> QuizResponse:
    return await service.get_quiz(user, quiz_id)


@router.put("/quizzes/{quiz_id}", response_model=QuizResponse)
async def update_quiz(
    quiz_id: UUID,
    payload: QuizUpdateRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: QuizService = Depends(get_quiz_service),  # noqa: B008
) -> QuizResponse:
    return await service.update_quiz(user, quiz_id, payload)


@router.delete(
    "/quizzes/{quiz_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_quiz(
    quiz_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: QuizService = Depends(get_quiz_service),  # noqa: B008
) -> Response:
    await service.delete_quiz(user, quiz_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
