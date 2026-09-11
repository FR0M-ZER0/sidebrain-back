from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class ProblemDetailError(Exception):
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.errors = errors


def _problem(
    status_code: int,
    title: str,
    detail: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://sidebrain.api/errors/{status_code}",
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status_code, content=body)


def register_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(ProblemDetailError)
    async def problem_detail_handler(
        _request: Request, error: ProblemDetailError
    ) -> JSONResponse:
        return _problem(
            error.status_code,
            error.title,
            error.detail,
            error.errors,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(part) for part in item["loc"]),
                "message": item["msg"],
            }
            for item in error.errors()
        ]
        return _problem(
            422, "Erro de validação", "Requisição inválida.", errors
        )

    @application.exception_handler(HTTPException)
    async def http_handler(
        _request: Request, error: HTTPException
    ) -> JSONResponse:
        title = (
            "Erro de autenticação" if error.status_code == 401 else "Erro HTTP"
        )
        return _problem(error.status_code, title, str(error.detail))

    @application.exception_handler(SQLAlchemyError)
    async def database_handler(
        _request: Request, _error: SQLAlchemyError
    ) -> JSONResponse:
        return _problem(
            500, "Erro interno", "Não foi possível processar a operação."
        )

    @application.exception_handler(Exception)
    async def unexpected_handler(
        _request: Request, _error: Exception
    ) -> JSONResponse:
        return _problem(
            500, "Erro interno", "Não foi possível processar a operação."
        )
