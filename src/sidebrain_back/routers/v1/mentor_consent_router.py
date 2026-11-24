from fastapi import APIRouter, Depends, Response, status

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.models.user_model import User
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.schemas.mentor_consent_schema import (
    MentorConsentAccept,
    MentorConsentResponse,
)
from sidebrain_back.services.auth_errors import ConflictError
from sidebrain_back.services.mentor_consent_service import (
    MentorConsentService,
    MentorConsentUnavailable,
    get_mentor_consent_service,
)

router = APIRouter(prefix="/v1/mentor-consent", tags=["Mentor"])


@router.get("", response_model=MentorConsentResponse)
async def get_mentor_consent(
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorConsentService = Depends(  # noqa: B008
        get_mentor_consent_service
    ),
) -> MentorConsentResponse:
    try:
        return await service.get_mentor_consent(user.usr_id)
    except MentorConsentUnavailable as error:
        raise ProblemDetailError(
            503, "Serviço indisponível", str(error)
        ) from error


@router.put("", response_model=MentorConsentResponse)
async def accept_mentor_consent(
    payload: MentorConsentAccept,
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorConsentService = Depends(  # noqa: B008
        get_mentor_consent_service
    ),
) -> MentorConsentResponse:
    try:
        return await service.accept_mentor_consent(
            user.usr_id, payload.notice_version
        )
    except ConflictError as error:
        raise ProblemDetailError(409, "Conflito", str(error)) from error
    except MentorConsentUnavailable as error:
        raise ProblemDetailError(
            503, "Serviço indisponível", str(error)
        ) from error


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_mentor_consent(
    user: User = Depends(get_current_user),  # noqa: B008
    service: MentorConsentService = Depends(  # noqa: B008
        get_mentor_consent_service
    ),
) -> Response:
    try:
        await service.revoke_mentor_consent(user.usr_id)
    except MentorConsentUnavailable as error:
        raise ProblemDetailError(
            503, "Serviço indisponível", str(error)
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
