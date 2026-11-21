from fastapi import Depends

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.ranking_repository import (
    RankingRepository,
    get_ranking_repository,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.ranking_schema import (
    RankingEntryResponse,
    RankingListResponse,
)


class RankingService:
    def __init__(self, repository: RankingRepository):
        self.repository = repository

    async def list_rankings(
        self, page: int = 1, page_size: int = 20
    ) -> RankingListResponse:
        total_items = await self.repository.count_ranked_users()
        offset = (page - 1) * page_size
        rows = await self.repository.list_rankings(
            offset=offset, limit=page_size
        )
        data = [
            RankingEntryResponse(
                position=row.position,
                user_id=row.user_id,
                name=row.name,
                xp=row.xp,
                missions_completed=row.missions_completed,
            )
            for row in rows
        ]
        return PaginatedResponse.build(
            data=data,
            page=page,
            page_size=page_size,
            total_items=total_items,
        )

    async def get_my_ranking(self, user: User) -> RankingEntryResponse:
        row = await self.repository.get_user_ranking(user.usr_id)
        if row is None:
            raise ProblemDetailError(
                404,
                "Não encontrado",
                "Usuário não encontrado.",
            )
        return RankingEntryResponse(
            position=row.position,
            user_id=row.user_id,
            name=row.name,
            xp=row.xp,
            missions_completed=row.missions_completed,
        )


def get_ranking_service(
    repository: RankingRepository = Depends(  # noqa: B008
        get_ranking_repository
    ),
) -> RankingService:
    return RankingService(repository)
