from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.badge_model import Badge
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.badge_repository import (
    BadgeRepository,
    get_badge_repository,
)
from sidebrain_back.schemas.badge_schema import (
    BadgeCreate,
    BadgeResponse,
    BadgeUpdate,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse


class BadgeService:
    def __init__(self, repository: BadgeRepository, db: AsyncSession):
        self.repository = repository
        self.db = db

    @staticmethod
    def _response(badge: Badge) -> BadgeResponse:
        return BadgeResponse.model_validate(badge)

    @staticmethod
    def _not_found() -> ProblemDetailError:
        return ProblemDetailError(
            404, "Não encontrado", "Badge não encontrado"
        )

    @staticmethod
    def _conflict() -> ProblemDetailError:
        return ProblemDetailError(
            409, "Conflito", "Já existe um badge ativo com este nome."
        )

    async def create_badge(
        self, _user: User, payload: BadgeCreate
    ) -> BadgeResponse:
        try:
            if await self.repository.name_exists(payload.name):
                raise self._conflict()
            badge = await self.repository.create(
                payload.name,
                payload.description,
                payload.rarity,
                payload.criteria,
                payload.criteria_value,
            )
            response = self._response(badge)
            await self.db.commit()
            return response
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível criar o badge."
            ) from error

    async def list_badges(
        self, user: User, page: int, page_size: int
    ) -> PaginatedResponse[BadgeResponse]:
        badges, total = await self.repository.list(
            user.usr_id, (page - 1) * page_size, page_size
        )
        return PaginatedResponse.build(
            [self._response(badge) for badge in badges],
            page,
            page_size,
            total,
        )

    async def get_badge(self, user: User, badge_id: UUID) -> BadgeResponse:
        badge = await self.repository.get(badge_id, user.usr_id)
        if badge is None:
            raise self._not_found()
        return self._response(badge)

    async def update_badge(
        self, user: User, badge_id: UUID, payload: BadgeUpdate
    ) -> BadgeResponse:
        badge = await self.repository.get(badge_id, user.usr_id)
        if badge is None:
            raise self._not_found()
        values = payload.model_dump(exclude_unset=True)
        try:
            if "name" in values and await self.repository.name_exists(
                values["name"], exclude_id=badge_id
            ):
                raise self._conflict()
            await self.repository.update(badge, values)
            response = self._response(badge)
            await self.db.commit()
            return response
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível atualizar o badge."
            ) from error

    async def delete_badge(self, user: User, badge_id: UUID) -> None:
        badge = await self.repository.get(badge_id, user.usr_id)
        if badge is None:
            raise self._not_found()
        try:
            await self.repository.soft_delete(badge)
            await self.db.commit()
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500, "Erro interno", "Não foi possível excluir o badge."
            ) from error


def get_badge_service(
    repository: BadgeRepository = Depends(get_badge_repository),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> BadgeService:
    return BadgeService(repository, db)
