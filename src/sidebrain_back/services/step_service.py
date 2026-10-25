from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.step_repository import (
    StepRepository,
    get_step_repository,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.step_schema import (
    StepCreate,
    StepResponse,
    StepSummaryResponse,
    StepUpdate,
)
from sidebrain_back.services.step_summary_service import (
    StepSummaryService,
    get_step_summary_service,
)


class StepService:
    def __init__(
        self,
        repository: StepRepository,
        db: AsyncSession,
        summary_service: StepSummaryService | None = None,
    ):
        self.repository = repository
        self.db = db
        self.summary_service = summary_service

    async def create_step(
        self, user: User, track_id: UUID, payload: StepCreate
    ) -> StepResponse:
        if (
            await self.repository.get_accessible_track(user.usr_id, track_id)
            is None
        ):
            raise ProblemDetailError(
                404, "Não encontrado", "Trilha não encontrada"
            )
        try:
            step = await self.repository.create(
                track_id, payload.level, payload.title
            )
            response = StepResponse.model_validate(step)
            await self.db.commit()
            return response
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível criar a etapa."
            ) from error

    async def list_steps(
        self, user: User, track_id: UUID, page: int, page_size: int
    ) -> PaginatedResponse[StepResponse]:
        if (
            await self.repository.get_accessible_track(user.usr_id, track_id)
            is None
        ):
            raise ProblemDetailError(
                404, "Não encontrado", "Trilha não encontrada"
            )
        steps, total = await self.repository.list(
            user.usr_id, track_id, (page - 1) * page_size, page_size
        )
        return PaginatedResponse.build(
            [StepResponse.model_validate(step) for step in steps],
            page,
            page_size,
            total,
        )

    async def get_step(
        self, user: User, track_id: UUID, step_id: UUID
    ) -> StepResponse:
        step = await self.repository.get(user.usr_id, track_id, step_id)
        if step is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Etapa não encontrada"
            )
        return StepResponse.model_validate(step)

    async def get_step_summary(
        self, user: User, track_id: UUID, step_id: UUID
    ) -> StepSummaryResponse:
        summary = await self.repository.get_summary(
            user.usr_id, track_id, step_id
        )
        if summary is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Etapa não encontrada"
            )
        return StepSummaryResponse(step_id=summary[0], summary=summary[1])

    async def generate_step_summary(
        self, user: User, track_id: UUID, step_id: UUID
    ) -> StepSummaryResponse:
        step_summary = await self.repository.get_summary(
            user.usr_id, track_id, step_id
        )
        if step_summary is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Etapa não encontrada"
            )
        if self.summary_service is None:
            raise ProblemDetailError(
                500,
                "Erro interno",
                "Não foi possível gerar o resumo da etapa.",
            )

        try:
            summary = await self.summary_service.generate_summary_for_step(
                user.usr_id, step_id
            )
            response = StepSummaryResponse(
                step_id=step_summary[0], summary=summary
            )
            await self.db.commit()
            return response
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500,
                "Erro interno",
                "Não foi possível gerar o resumo da etapa.",
            ) from error

    async def update_step(
        self,
        user: User,
        track_id: UUID,
        step_id: UUID,
        payload: StepUpdate,
    ) -> StepResponse:
        step = await self.repository.get(user.usr_id, track_id, step_id)
        if step is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Etapa não encontrada"
            )
        try:
            await self.repository.update(step, payload.level, payload.title)
            response = StepResponse.model_validate(step)
            await self.db.commit()
            return response
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível atualizar a etapa."
            ) from error

    async def delete_step(
        self, user: User, track_id: UUID, step_id: UUID
    ) -> None:
        step = await self.repository.get(user.usr_id, track_id, step_id)
        if step is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Etapa não encontrada"
            )
        try:
            await self.repository.soft_delete(step)
            await self.db.commit()
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível excluir a etapa."
            ) from error


def get_step_service(
    repository: StepRepository = Depends(get_step_repository),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    summary_service: StepSummaryService = Depends(  # noqa: B008
        get_step_summary_service
    ),
) -> StepService:
    return StepService(repository, db, summary_service)
