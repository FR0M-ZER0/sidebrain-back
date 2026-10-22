from fastapi import APIRouter, Depends, Query

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.ranking_schema import (
    RankingEntryResponse,
    RankingListResponse,
)
from sidebrain_back.services.ranking_service import (
    RankingService,
    get_ranking_service,
)

router = APIRouter(prefix="/v1/rankings", tags=["rankings"])


@router.get("", response_model=PaginatedResponse[RankingEntryResponse])
async def list_rankings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
    service: RankingService = Depends(get_ranking_service),  # noqa: B008
) -> RankingListResponse:
    return await service.list_rankings(page=page, page_size=page_size)


@router.get("/me", response_model=RankingEntryResponse)
async def get_my_ranking(
    user: User = Depends(get_current_user),  # noqa: B008
    service: RankingService = Depends(get_ranking_service),  # noqa: B008
) -> RankingEntryResponse:
    return await service.get_my_ranking(user=user)
