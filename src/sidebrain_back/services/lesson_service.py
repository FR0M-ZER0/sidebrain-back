from uuid import UUID

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.lesson_repository import (
    LessonRepository,
    get_lesson_repository,
)
from sidebrain_back.schemas.lesson_schema import (
    LessonCreateRequest,
    LessonResponse,
    LessonUpdateRequest,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse


class LessonService:
    def __init__(self, repository: LessonRepository, db: AsyncSession):
        self.repository = repository
        self.db = db

    async def _require_step(self, user_id: UUID, step_id: UUID) -> Step:
        step = await self.repository.get_accessible_step(user_id, step_id)
        if step is None:
            raise ProblemDetailError(
                404,
                "Não encontrado",
                "Etapa não encontrada.",
            )
        return step

    async def _require_lesson(self, user_id: UUID, lesson_id: UUID) -> Lesson:
        lesson = await self.repository.get(user_id, lesson_id)
        if lesson is None:
            raise ProblemDetailError(
                404,
                "Não encontrado",
                "Lição não encontrada.",
            )
        return lesson

    async def _ensure_position_available(
        self,
        step_id: UUID,
        position: int,
        exclude_lesson_id: UUID | None = None,
    ) -> None:
        if await self.repository.position_exists(
            step_id,
            position,
            exclude_lesson_id,
        ):
            raise self._position_conflict()

    async def create_lesson(
        self,
        user: User,
        step_id: UUID,
        payload: LessonCreateRequest,
    ) -> LessonResponse:
        try:
            await self._require_step(user.usr_id, step_id)
            await self._ensure_position_available(step_id, payload.position)
            lesson = await self.repository.create(
                step_id,
                payload.title,
                payload.text,
                payload.position,
            )
            response = LessonResponse.model_validate(lesson)
            await self.db.commit()
            return response
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except IntegrityError as error:
            await self.db.rollback()
            if self._is_unique_violation(error):
                raise self._position_conflict() from error
            raise self._internal_error("criar") from error
        except Exception as error:
            await self.db.rollback()
            raise self._internal_error("criar") from error

    async def list_lessons_by_step_id(
        self,
        user: User,
        step_id: UUID,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[LessonResponse]:
        await self._require_step(user.usr_id, step_id)
        lessons, total = await self.repository.list_by_step_id(
            user.usr_id,
            step_id,
            (page - 1) * page_size,
            page_size,
        )
        return PaginatedResponse.build(
            [LessonResponse.model_validate(lesson) for lesson in lessons],
            page,
            page_size,
            total,
        )

    async def get_lesson(
        self,
        user: User,
        lesson_id: UUID,
    ) -> LessonResponse:
        lesson = await self._require_lesson(user.usr_id, lesson_id)
        return LessonResponse.model_validate(lesson)

    async def update_lesson(
        self,
        user: User,
        lesson_id: UUID,
        payload: LessonUpdateRequest,
    ) -> LessonResponse:
        try:
            lesson = await self._require_lesson(user.usr_id, lesson_id)
            await self._ensure_position_available(
                lesson.lsn_step_id,
                payload.position,
                lesson.lsn_id,
            )
            await self.repository.update(
                lesson,
                payload.title,
                payload.text,
                payload.status,
                payload.position,
            )
            response = LessonResponse.model_validate(lesson)
            await self.db.commit()
            return response
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except IntegrityError as error:
            await self.db.rollback()
            if self._is_unique_violation(error):
                raise self._position_conflict() from error
            raise self._internal_error("atualizar") from error
        except Exception as error:
            await self.db.rollback()
            raise self._internal_error("atualizar") from error

    async def delete_lesson(self, user: User, lesson_id: UUID) -> None:
        try:
            lesson = await self._require_lesson(user.usr_id, lesson_id)
            await self.repository.delete(lesson)
            await self.db.commit()
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except IntegrityError as error:
            await self.db.rollback()
            raise self._internal_error("excluir") from error
        except Exception as error:
            await self.db.rollback()
            raise self._internal_error("excluir") from error

    @staticmethod
    def _position_conflict() -> ProblemDetailError:
        return ProblemDetailError(
            409,
            "Conflito",
            "Já existe uma lição nesta posição para a etapa.",
        )

    @staticmethod
    def _internal_error(action: str) -> ProblemDetailError:
        return ProblemDetailError(
            500,
            "Erro interno",
            f"Não foi possível {action} a lição.",
        )

    @staticmethod
    def _is_unique_violation(error: IntegrityError) -> bool:
        candidate = error.orig
        while candidate is not None:
            sqlstate = getattr(candidate, "sqlstate", None) or getattr(
                candidate, "pgcode", None
            )
            if sqlstate == "23505":
                return True
            candidate = getattr(candidate, "__cause__", None)
        return False


def get_lesson_service(
    repository: LessonRepository = Depends(get_lesson_repository),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> LessonService:
    return LessonService(repository, db)
