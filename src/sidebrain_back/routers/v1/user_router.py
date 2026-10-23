from fastapi import APIRouter, Depends, Request, Response, status

from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.core.rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.routers.v1.auth_router import (
    _client_origin,
    get_current_user,
)
from sidebrain_back.schemas.user_schema import (
    PasswordUpdateRequest,
    UserMeResponse,
    UserUpdateRequest,
)
from sidebrain_back.services.auth_errors import (
    AuthenticationError,
    ConflictError,
    DomainValidationError,
    ResourceNotFoundError,
)
from sidebrain_back.services.user_service import UserService, get_user_service

router = APIRouter(prefix="/v1/users", tags=["Users"])


@router.get("/me", response_model=UserMeResponse)
async def get_user(
    user: User = Depends(get_current_user),  # noqa: B008
    service: UserService = Depends(get_user_service),  # noqa: B008
) -> UserMeResponse:
    try:
        return await service.get_user(user)
    except ResourceNotFoundError as error:
        raise _not_found() from error


@router.put("/me", response_model=UserMeResponse)
async def update_user(
    payload: UserUpdateRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: UserService = Depends(get_user_service),  # noqa: B008
) -> UserMeResponse:
    try:
        return await service.update_user(user, payload)
    except ResourceNotFoundError as error:
        raise _not_found() from error
    except ConflictError as error:
        raise ProblemDetailError(
            409,
            "Conflito",
            "O e-mail informado já está em uso.",
        ) from error


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(
    payload: PasswordUpdateRequest,
    request: Request,
    user: User = Depends(get_current_user),  # noqa: B008
    service: UserService = Depends(get_user_service),  # noqa: B008
) -> Response:
    try:
        await service.update_password(user, payload, _client_origin(request))
    except AuthenticationError as error:
        raise ProblemDetailError(
            401,
            "Erro de autenticação",
            "Senha atual inválida.",
        ) from error
    except ResourceNotFoundError as error:
        raise _not_found() from error
    except DomainValidationError as error:
        raise ProblemDetailError(
            422,
            "Erro de validação",
            str(error),
        ) from error
    except RateLimitExceeded as error:
        raise ProblemDetailError(
            429,
            "Muitas tentativas",
            "Tente novamente mais tarde.",
            headers={"Retry-After": str(error.retry_after)},
        ) from error
    except RateLimitUnavailable as error:
        raise ProblemDetailError(
            503,
            "Serviço indisponível",
            "Não foi possível validar o limite de tentativas.",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user: User = Depends(get_current_user),  # noqa: B008
    service: UserService = Depends(get_user_service),  # noqa: B008
) -> Response:
    try:
        await service.delete_user(user)
    except ResourceNotFoundError as error:
        raise _not_found() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _not_found() -> ProblemDetailError:
    return ProblemDetailError(
        404,
        "Não encontrado",
        "Usuário não encontrado.",
    )
