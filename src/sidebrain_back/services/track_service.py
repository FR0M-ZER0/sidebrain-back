from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.track_repository import (
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
    def __init__(self, repository: TrackRepository, db: AsyncSession):
        self.repository = repository
        self.db = db

    async def create_track(
        self, user: User, payload: TrackCreate
    ) -> TrackResponse:
        try:
            track = await self.repository.create(
                user, payload.title, payload.description
            )
            await self.db.commit()
            loaded_track = await self.repository.get(user.usr_id, track.trk_id)
            if loaded_track is None:
                raise ProblemDetailError(
                    500,
                    "Erro interno",
                    "Não foi possível carregar a trilha criada.",
                )
            return TrackResponse.model_validate(loaded_track)
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
            await self.db.commit()
            loaded_track = await self.repository.get(user.usr_id, track_id)
            if loaded_track is None:
                raise ProblemDetailError(
                    500,
                    "Erro interno",
                    "Não foi possível carregar a trilha atualizada.",
                )
            return TrackResponse.model_validate(loaded_track)
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
