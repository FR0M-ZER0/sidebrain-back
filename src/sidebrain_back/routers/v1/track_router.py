import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from sidebrain_back.core.auth import get_current_user
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.generation_schema import (
    GenerationAccepted,
    PrepareNextAccepted,
    PrepareNextSkipped,
)
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.track_schema import (
    TrackCreate,
    TrackResponse,
    TrackUpdate,
)
from sidebrain_back.services.track_service import (
    TrackService,
    get_track_service,
)

router = APIRouter(prefix="/v1/tracks", tags=["Tracks"])


@router.get("/generations/{request_id}/events")
async def stream_generation_progress(
    request_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> StreamingResponse:
    progress = await service.get_generation_progress(user, request_id)

    async def events():
        current = progress
        elapsed_polls = 0
        yield f"event: generation\ndata: {current.model_dump_json()}\n\n"
        while True:
            if current.status.value in {"succeeded", "failed"}:
                break
            await asyncio.sleep(1)
            if await request.is_disconnected():
                break
            updated = await service.get_generation_progress(user, request_id)
            if updated.status != current.status:
                current = updated
                yield (
                    f"event: generation\ndata: "
                    f"{current.model_dump_json()}\n\n"
                )
            else:
                elapsed_polls += 1
                if elapsed_polls % 15 == 0:
                    yield ": keep-alive\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "", response_model=GenerationAccepted, status_code=status.HTTP_202_ACCEPTED
)
async def create_track(
    payload: TrackCreate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> GenerationAccepted:
    return await service.create_track(user, payload)


@router.post(
    "/{track_id}/steps/{step_id}/prepare-next",
    response_model=PrepareNextAccepted | PrepareNextSkipped,
    status_code=status.HTTP_202_ACCEPTED,
)
async def prepare_next_step(
    track_id: UUID,
    step_id: UUID,
    response: Response,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> PrepareNextAccepted | PrepareNextSkipped:
    result = await service.prepare_next_step(user, track_id, step_id)
    if isinstance(result, PrepareNextSkipped):
        response.status_code = status.HTTP_200_OK
    return result


@router.get("", response_model=PaginatedResponse[TrackResponse])
async def list_tracks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> PaginatedResponse[TrackResponse]:
    return await service.list_tracks(user, page, page_size)


@router.get("/{track_id}", response_model=TrackResponse)
async def get_track(
    track_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> TrackResponse:
    return await service.get_track(user, track_id)


@router.patch("/{track_id}", response_model=TrackResponse)
async def update_track(
    track_id: UUID,
    payload: TrackUpdate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> TrackResponse:
    return await service.update_track(user, track_id, payload)


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(
    track_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: TrackService = Depends(get_track_service),  # noqa: B008
) -> Response:
    await service.delete_track(user, track_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
