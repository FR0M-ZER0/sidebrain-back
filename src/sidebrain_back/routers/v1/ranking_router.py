from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from sidebrain_back.models.user_model import User
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.ranking_schema import (
    RankingEntryResponse,
    RankingListResponse,
)
from sidebrain_back.services.ranking_service import (
    RankingService,
    get_ranking_service,
)
from sidebrain_back.services.ranking_stream_service import (
    RankingStreamService,
    get_ranking_stream_service,
)

router = APIRouter(prefix="/v1/rankings", tags=["Rankings"])


@router.get("/events")
async def stream_rankings(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
    service: RankingStreamService = Depends(  # noqa: B008
        get_ranking_stream_service
    ),
) -> StreamingResponse:
    initial = await service.list_rankings(page, page_size)
    return StreamingResponse(
        service.stream(
            request,
            "ranking",
            initial,
            lambda: service.list_rankings(page, page_size),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/me/events")
async def stream_my_ranking(
    request: Request,
    user: User = Depends(get_current_user),  # noqa: B008
    service: RankingStreamService = Depends(  # noqa: B008
        get_ranking_stream_service
    ),
) -> StreamingResponse:
    user_id = user.usr_id
    initial = await service.get_my_ranking(user_id)
    return StreamingResponse(
        service.stream(
            request,
            "xp",
            initial,
            lambda: service.get_my_ranking(user_id),
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
