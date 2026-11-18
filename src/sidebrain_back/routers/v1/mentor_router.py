import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import StreamingResponse

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.mentor_generation_repository import (
    MentorGenerationConflict,
)
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.mentor_schema import (
    MentorConversationCreate,
    MentorConversationListParams,
    MentorConversationResponse,
    MentorGenerationAccepted,
    MentorGenerationResponse,
    MentorMessageCreate,
    MentorMessageResponse,
)
from sidebrain_back.schemas.pagination_schema import (
    PaginatedResponse,
    PaginationParams,
)
from sidebrain_back.services.mentor_consent_service import (
    MentorConsentUnavailable,
)
from sidebrain_back.services.mentor_service import (
    MentorConsentRequired,
    MentorNotFound,
    MentorService,
    get_mentor_service,
)

router = APIRouter(prefix="/v1/mentor-conversations", tags=["Mentor"])


def _problem(error: Exception) -> ProblemDetailError:
    if isinstance(error, MentorNotFound):
        return ProblemDetailError(404, "Não encontrado", str(error))
    if isinstance(error, MentorConsentRequired):
        return ProblemDetailError(
            403,
            "Autorização necessária",
            str(error),
            error_code="mentor-consent-required",
        )
    if isinstance(error, MentorGenerationConflict):
        return ProblemDetailError(409, "Conflito", str(error))
    return ProblemDetailError(503, "Serviço indisponível", str(error))


@router.post(
    "",
    response_model=MentorConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mentor_conversation(
    payload: MentorConversationCreate,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> MentorConversationResponse:
    try:
        return await service.create_mentor_conversation(
            user.usr_id, payload.track_id
        )
    except (MentorNotFound, MentorConsentUnavailable) as error:
        raise _problem(error) from error


@router.get("", response_model=PaginatedResponse[MentorConversationResponse])
async def list_mentor_conversations(
    params: Annotated[MentorConversationListParams, Query()],
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> PaginatedResponse[MentorConversationResponse]:
    return await service.list_mentor_conversations(
        user.usr_id, params.page, params.page_size, params.track_id
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_mentor_conversations(
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> Response:
    try:
        await service.delete_mentor_conversations(user.usr_id)
    except MentorConsentUnavailable as error:
        raise _problem(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{conversation_id}/messages",
    response_model=MentorGenerationAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_mentor_message(
    conversation_id: UUID,
    payload: MentorMessageCreate,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> MentorGenerationAccepted:
    try:
        return await service.create_mentor_message(
            user.usr_id, conversation_id, idempotency_key, payload
        )
    except (
        MentorNotFound,
        MentorConsentRequired,
        MentorGenerationConflict,
        MentorConsentUnavailable,
    ) as error:
        raise _problem(error) from error


@router.get(
    "/{conversation_id}/generations/{generation_id}",
    response_model=MentorGenerationResponse,
)
async def get_mentor_generation(
    conversation_id: UUID,
    generation_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> MentorGenerationResponse:
    try:
        return await service.get_mentor_generation(
            user.usr_id, conversation_id, generation_id
        )
    except MentorNotFound as error:
        raise _problem(error) from error


@router.get("/{conversation_id}/generations/{generation_id}/events")
async def stream_mentor_generation(
    conversation_id: UUID,
    generation_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> StreamingResponse:
    user_id = user.usr_id
    try:
        initial = await service.get_mentor_generation_event(
            user_id, conversation_id, generation_id
        )
    except MentorNotFound as error:
        raise _problem(error) from error

    async def events():
        current = initial
        polls = 0
        yield f"event: generation\ndata: {current.model_dump_json()}\n\n"
        while current.generation.status not in {"completed", "failed"}:
            await asyncio.sleep(1)
            if await request.is_disconnected():
                return
            try:
                updated = await service.get_mentor_generation_event(
                    user_id, conversation_id, generation_id
                )
            except Exception:
                yield (
                    'event: error\ndata: {"detail":"Stream indisponível."}\n\n'
                )
                return
            if updated != current:
                current = updated
                yield (
                    f"event: generation\ndata: {current.model_dump_json()}\n\n"
                )
            else:
                polls += 1
                if polls % 15 == 0:
                    yield ": keep-alive\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/{conversation_id}/generations/{generation_id}/retry",
    response_model=MentorGenerationAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_mentor_generation(
    conversation_id: UUID,
    generation_id: UUID,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> MentorGenerationAccepted:
    try:
        return await service.retry_mentor_generation(
            user.usr_id, conversation_id, generation_id, idempotency_key
        )
    except (
        MentorNotFound,
        MentorConsentRequired,
        MentorGenerationConflict,
        MentorConsentUnavailable,
    ) as error:
        raise _problem(error) from error


@router.get(
    "/{conversation_id}/messages/{message_id}",
    response_model=MentorMessageResponse,
)
async def get_mentor_message(
    conversation_id: UUID,
    message_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> MentorMessageResponse:
    try:
        return await service.get_mentor_message(
            user.usr_id, conversation_id, message_id
        )
    except MentorNotFound as error:
        raise _problem(error) from error


@router.get(
    "/{conversation_id}/messages",
    response_model=PaginatedResponse[MentorMessageResponse],
)
async def list_mentor_messages(
    conversation_id: UUID,
    params: Annotated[PaginationParams, Query()],
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> PaginatedResponse[MentorMessageResponse]:
    try:
        return await service.list_mentor_messages(
            user.usr_id, conversation_id, params.page, params.page_size
        )
    except MentorNotFound as error:
        raise _problem(error) from error


@router.get("/{conversation_id}", response_model=MentorConversationResponse)
async def get_mentor_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> MentorConversationResponse:
    try:
        return await service.get_mentor_conversation(
            user.usr_id, conversation_id
        )
    except MentorNotFound as error:
        raise _problem(error) from error


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mentor_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorService = Depends(get_mentor_service),  # noqa: B008
) -> Response:
    try:
        await service.delete_mentor_conversations(user.usr_id, conversation_id)
    except (MentorNotFound, MentorConsentUnavailable) as error:
        raise _problem(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
