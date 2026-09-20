from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.quiz_repository import (
    QuizRepository,
    get_quiz_repository,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.quiz_schema import (
    QuizCreateRequest,
    QuizResponse,
    QuizUpdateRequest,
)


class QuizService:
    def __init__(self, repository: QuizRepository, db: AsyncSession):
        self.repository = repository
        self.db = db

    async def _require_lesson(
        self,
        user_id: UUID,
        lesson_id: UUID,
    ) -> Lesson:
        lesson = await self.repository.get_accessible_lesson(
            user_id,
            lesson_id,
        )
        if lesson is None:
            raise ProblemDetailError(
                404,
                "Não encontrado",
                "Aula não encontrada.",
            )
        return lesson

    async def _require_quiz(
        self,
        user_id: UUID,
        quiz_id: UUID,
    ) -> Quiz:
        quiz = await self.repository.get_accessible_quiz(user_id, quiz_id)
        if quiz is None:
            raise ProblemDetailError(
                404,
                "Não encontrado",
                "Quiz não encontrado.",
            )
        return quiz

    async def create_quiz(
        self,
        user: User,
        lesson_id: UUID,
        payload: QuizCreateRequest,
    ) -> QuizResponse:
        try:
            await self._require_lesson(user.usr_id, lesson_id)
            quiz = await self.repository.create(lesson_id, payload.question)
            response = QuizResponse.model_validate(quiz)
            await self.db.commit()
            return response
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500,
                "Erro interno",
                "Não foi possível criar o quiz.",
            ) from error

    async def list_quizzes_by_lesson(
        self,
        user: User,
        lesson_id: UUID,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[QuizResponse]:
        await self._require_lesson(user.usr_id, lesson_id)
        quizzes, total = await self.repository.list_by_lesson_id(
            lesson_id,
            (page - 1) * page_size,
            page_size,
        )
        return PaginatedResponse.build(
            [QuizResponse.model_validate(quiz) for quiz in quizzes],
            page,
            page_size,
            total,
        )

    async def get_quiz(
        self,
        user: User,
        quiz_id: UUID,
    ) -> QuizResponse:
        quiz = await self._require_quiz(user.usr_id, quiz_id)
        return QuizResponse.model_validate(quiz)

    async def update_quiz(
        self,
        user: User,
        quiz_id: UUID,
        payload: QuizUpdateRequest,
    ) -> QuizResponse:
        try:
            quiz = await self._require_quiz(user.usr_id, quiz_id)
            await self.repository.update(quiz, payload.question)
            response = QuizResponse.model_validate(quiz)
            await self.db.commit()
            return response
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500,
                "Erro interno",
                "Não foi possível atualizar o quiz.",
            ) from error

    async def delete_quiz(self, user: User, quiz_id: UUID) -> None:
        try:
            quiz = await self._require_quiz(user.usr_id, quiz_id)
            await self.repository.soft_delete(quiz)
            await self.db.commit()
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500,
                "Erro interno",
                "Não foi possível excluir o quiz.",
            ) from error


def get_quiz_service(
    repository: QuizRepository = Depends(get_quiz_repository),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> QuizService:
    return QuizService(repository, db)
