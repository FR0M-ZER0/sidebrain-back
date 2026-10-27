from uuid import UUID

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.mission_repository import (
    MissionRepository,
    get_mission_repository,
)
from sidebrain_back.schemas.mission_schema import (
    MissionCreate,
    MissionListItemResponse,
    MissionListParams,
    MissionResponse,
    MissionTrackGroupResponse,
    MissionUpdate,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse


class MissionService:
    def __init__(self, repository: MissionRepository, db: AsyncSession):
        self.repository = repository
        self.db = db

    async def list_missions(
        self, user: User, params: MissionListParams
    ) -> PaginatedResponse[MissionTrackGroupResponse]:
        rows, total = await self.repository.list(
            user.usr_id,
            (params.page - 1) * params.page_size,
            params.page_size,
            **params.model_dump(exclude={"page", "page_size"}),
        )
        groups: dict[UUID, MissionTrackGroupResponse] = {}
        for row in rows:
            if row.track_id not in groups:
                groups[row.track_id] = MissionTrackGroupResponse(
                    track_id=row.track_id,
                    track_title=row.track_title,
                    track_icon=row.track_icon,
                )
            mission = MissionResponse.model_validate(row.mission)
            groups[row.track_id].missions.append(
                MissionListItemResponse(
                    **mission.model_dump(),
                    step_title=row.step_title,
                    status=row.status,
                    score=row.score,
                    last_activity_at=row.last_activity_at,
                )
            )
        return PaginatedResponse.build(
            list(groups.values()), params.page, params.page_size, total
        )

    async def _require_step(self, user_id: UUID, step_id: UUID) -> Step:
        step = await self.repository.get_accessible_step(user_id, step_id)
        if step is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Etapa não encontrada."
            )
        return step

    async def _require_mission(
        self, user_id: UUID, mission_id: UUID
    ) -> Mission:
        mission = await self.repository.get(user_id, mission_id)
        if mission is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Missão não encontrada."
            )
        return mission

    async def create_mission(
        self, user: User, step_id: UUID, payload: MissionCreate
    ) -> MissionResponse:
        try:
            await self._require_step(user.usr_id, step_id)
            mission = await self.repository.create(
                step_id,
                payload.title,
                payload.difficulty,
                payload.xp_reward,
                payload.criteria,
                payload.criteria_value,
            )
            response = MissionResponse.model_validate(mission)
            await self.db.commit()
            return response
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except IntegrityError as error:
            await self.db.rollback()
            raise self._internal_error("criar") from error
        except Exception as error:
            await self.db.rollback()
            raise self._internal_error("criar") from error

    async def list_missions_by_step_id(
        self, user: User, step_id: UUID, page: int, page_size: int
    ) -> PaginatedResponse[MissionResponse]:
        await self._require_step(user.usr_id, step_id)
        missions, total = await self.repository.list_by_step_id(
            user.usr_id, step_id, (page - 1) * page_size, page_size
        )
        return PaginatedResponse.build(
            [MissionResponse.model_validate(item) for item in missions],
            page,
            page_size,
            total,
        )

    async def get_mission(
        self, user: User, mission_id: UUID
    ) -> MissionResponse:
        mission = await self._require_mission(user.usr_id, mission_id)
        return MissionResponse.model_validate(mission)

    async def update_mission(
        self, user: User, mission_id: UUID, payload: MissionUpdate
    ) -> MissionResponse:
        try:
            mission = await self._require_mission(user.usr_id, mission_id)
            values = payload.model_dump(exclude_unset=True)
            await self.repository.update(mission, values)
            response = MissionResponse.model_validate(mission)
            await self.db.commit()
            return response
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except IntegrityError as error:
            await self.db.rollback()
            raise self._internal_error("atualizar") from error
        except Exception as error:
            await self.db.rollback()
            raise self._internal_error("atualizar") from error

    async def delete_mission(self, user: User, mission_id: UUID) -> None:
        try:
            mission = await self._require_mission(user.usr_id, mission_id)
            await self.repository.soft_delete(mission)
            await self.db.commit()
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except Exception as error:
            await self.db.rollback()
            raise self._internal_error("excluir") from error

    @staticmethod
    def _internal_error(action: str) -> ProblemDetailError:
        return ProblemDetailError(
            500, "Erro interno", f"Não foi possível {action} a missão."
        )


def get_mission_service(
    repository: MissionRepository = Depends(get_mission_repository),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MissionService:
    return MissionService(repository, db)
