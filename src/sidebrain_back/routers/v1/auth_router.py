from fastapi import APIRouter, Depends, Request, Response, status

from sidebrain_back.core.auth import get_bearer_token
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.core.rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
)
from sidebrain_back.core.ws_tickets import WsTicketUnavailable
from sidebrain_back.models.user_model import User
from sidebrain_back.schemas.auth_schema import AuthResponse, UserLoginRequest
from sidebrain_back.schemas.job_update_schema import (
    WsTicketRequest,
    WsTicketResponse,
)
from sidebrain_back.schemas.user_schema import UserRegisterRequest
from sidebrain_back.services.auth_errors import (
    AuthenticationError,
    ConflictError,
)
from sidebrain_back.services.auth_service import AuthService, get_auth_service
from sidebrain_back.services.job_update_service import (
    JobUpdateService,
    get_job_update_service,
)

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    payload: UserRegisterRequest,
    service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> AuthResponse:
    try:
        return await service.register_user(payload)
    except ConflictError as error:
        raise ProblemDetailError(
            409,
            "Conflito",
            "O e-mail informado já está em uso.",
        ) from error


@router.post("/login", response_model=AuthResponse)
async def login_user(
    payload: UserLoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> AuthResponse:
    try:
        return await service.login_user(payload, _client_origin(request))
    except AuthenticationError as error:
        raise ProblemDetailError(
            401,
            "Erro de autenticação",
            "Credenciais inválidas.",
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


async def get_current_user(
    token: str = Depends(get_bearer_token),  # noqa: B008
    service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> User:
    try:
        return await service.authenticate_user_token(token)
    except AuthenticationError as error:
        raise ProblemDetailError(
            401,
            "Erro de autenticação",
            "Credencial de autenticação ausente ou inválida.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def _client_origin(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


@router.post("/ws-ticket", response_model=WsTicketResponse)
async def create_ws_ticket(
    payload: WsTicketRequest,
    response: Response,
    user: User = Depends(get_current_user),  # noqa: B008
    service: JobUpdateService = Depends(get_job_update_service),  # noqa: B008
) -> WsTicketResponse:
    try:
        ticket = await service.issue_ticket(user, payload)
    except WsTicketUnavailable as error:
        raise ProblemDetailError(
            503,
            "Serviço indisponível",
            "Não foi possível emitir a credencial temporária.",
        ) from error
    response.headers["Cache-Control"] = "no-store"
    return WsTicketResponse(ticket=ticket)
