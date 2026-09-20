from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.track_repository import (
    StepProgressContext,
    TrackRepository,
    get_track_repository,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.track_schema import (
    TrackCreate,
    TrackResponse,
    TrackUpdate,
)


class TrackService:
    PROGRESS_THRESHOLD = 0.80

    def __init__(self, repository: TrackRepository, db: AsyncSession):
        self.repository = repository
        self.db = db

    @classmethod
    def completion_ratio(
        cls, active_lessons_total: int, active_lessons_completed: int
    ) -> float:
        if active_lessons_total <= 0:
            return 0.0
        return min(active_lessons_completed, active_lessons_total) / (
            active_lessons_total
        )

    @classmethod
    def should_prepare_next_step(
        cls, progress: StepProgressContext | tuple[int, int] | object
    ) -> bool:
        if isinstance(progress, StepProgressContext):
            ratio = progress.completion_ratio
            total = progress.active_lessons_total
        else:
            total, completed = progress  # type: ignore[misc]
            ratio = cls.completion_ratio(total, completed)
        return total > 0 and ratio >= cls.PROGRESS_THRESHOLD

    async def get_next_step_to_prepare(self, step_id: UUID):
        progress = await self.repository.get_step_progress(step_id)
        if not self.should_prepare_next_step(progress):
            return None
        return await self.repository.get_next_eligible_step(step_id)

    async def enqueue_next_step_preparation(self, step_id: UUID):
        next_step = await self.get_next_step_to_prepare(step_id)
        if next_step is None:
            return None
        from sidebrain_back.tasks.prepare_next_step_content_task import (
            prepare_next_step_content_task,
        )

        return prepare_next_step_content_task.delay(str(next_step.stp_id))

    async def create_track(
        self, user: User, payload: TrackCreate
    ) -> TrackResponse:
        try:
            track = await self.repository.create(
                user, payload.title, payload.description
            )
            response = TrackResponse.model_validate(track)
            await self.db.commit()
            return response
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível criar a trilha."
            ) from error

    async def list_tracks(
        self, user: User, page: int, page_size: int
    ) -> PaginatedResponse[TrackResponse]:
        tracks, total = await self.repository.list(
            user.usr_id, (page - 1) * page_size, page_size
        )
        return PaginatedResponse.build(
            [TrackResponse.model_validate(track) for track in tracks],
            page,
            page_size,
            total,
        )

    async def get_track(self, user: User, track_id: UUID) -> TrackResponse:
        track = await self.repository.get(user.usr_id, track_id)
        if track is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Trilha não encontrada"
            )
        return TrackResponse.model_validate(track)

    async def update_track(
        self, user: User, track_id: UUID, payload: TrackUpdate
    ) -> TrackResponse:
        track = await self.repository.get(user.usr_id, track_id)
        if track is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Trilha não encontrada"
            )
        try:
            await self.repository.update(
                track,
                payload.title,
                payload.description,
                "description" in payload.model_fields_set,
            )
            response = TrackResponse.model_validate(track)
            await self.db.commit()
            return response
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível atualizar a trilha."
            ) from error

    async def delete_track(self, user: User, track_id: UUID) -> None:
        track = await self.repository.get(user.usr_id, track_id)
        if track is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Trilha não encontrada"
            )
        try:
            await self.repository.soft_delete(track)
            await self.db.commit()
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível excluir a trilha."
            ) from error


def get_track_service(
    repository: TrackRepository = Depends(get_track_repository),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TrackService:
    return TrackService(repository, db)
