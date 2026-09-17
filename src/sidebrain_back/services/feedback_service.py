from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.feedback_repository import (
    FeedbackRepository,
    get_feedback_repository,
)
from sidebrain_back.schemas.feedback_schema import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse


class FeedbackService:
    def __init__(self, repository: FeedbackRepository, db: AsyncSession):
        self.repository = repository
        self.db = db

    async def create_feedback(
        self, user: User, lesson_id: UUID, payload: FeedbackCreate
    ) -> FeedbackResponse:
        if not await self.repository.lesson_exists(lesson_id):
            raise ProblemDetailError(
                404, "Não encontrado", "Aula não encontrada"
            )
        try:
            feedback = await self.repository.create(
                lesson_id, user.usr_id, payload.text
            )
            await self.db.commit()
            loaded = await self.repository.get(feedback.fbk_id)
            if loaded is None:
                raise ProblemDetailError(
                    500,
                    "Erro interno",
                    "Não foi possível carregar o feedback criado.",
                )
            return FeedbackResponse.model_validate(loaded)
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível criar o feedback."
            ) from error

    async def list_feedbacks_by_lesson(
        self, lesson_id: UUID, page: int, page_size: int
    ) -> PaginatedResponse[FeedbackResponse]:
        if not await self.repository.lesson_exists(lesson_id):
            raise ProblemDetailError(
                404, "Não encontrado", "Aula não encontrada"
            )
        feedbacks, total = await self.repository.list_by_lesson_id(
            lesson_id, (page - 1) * page_size, page_size
        )
        return PaginatedResponse.build(
            [FeedbackResponse.model_validate(item) for item in feedbacks],
            page,
            page_size,
            total,
        )

    async def get_feedback(self, feedback_id: UUID) -> FeedbackResponse:
        feedback = await self.repository.get(feedback_id)
        if feedback is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Feedback não encontrado"
            )
        return FeedbackResponse.model_validate(feedback)

    async def update_feedback(
        self, user: User, feedback_id: UUID, payload: FeedbackUpdate
    ) -> FeedbackResponse:
        feedback = await self.repository.get(feedback_id)
        if feedback is None or feedback.fbk_user_id != user.usr_id:
            raise ProblemDetailError(
                404, "Não encontrado", "Feedback não encontrado"
            )
        try:
            await self.repository.update(feedback, payload.text)
            await self.db.commit()
            loaded = await self.repository.get(feedback_id)
            if loaded is None:
                raise ProblemDetailError(
                    500,
                    "Erro interno",
                    "Não foi possível carregar o feedback atualizado.",
                )
            return FeedbackResponse.model_validate(loaded)
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível atualizar o feedback."
            ) from error

    async def delete_feedback(self, user: User, feedback_id: UUID) -> None:
        feedback = await self.repository.get(feedback_id)
        if feedback is None or feedback.fbk_user_id != user.usr_id:
            raise ProblemDetailError(
                404, "Não encontrado", "Feedback não encontrado"
            )
        try:
            await self.repository.soft_delete(feedback)
            await self.db.commit()
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível excluir o feedback."
            ) from error


def get_feedback_service(
    repository: FeedbackRepository = Depends(get_feedback_repository),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> FeedbackService:
    return FeedbackService(repository, db)
