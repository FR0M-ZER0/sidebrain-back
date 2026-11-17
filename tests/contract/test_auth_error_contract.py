from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from sidebrain_back.core.errors import (
    ProblemDetailError,
    register_error_handlers,
)


def _client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/unauthorized")
    async def unauthorized():
        raise HTTPException(
            401,
            "Credencial de autenticação ausente ou inválida.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.get("/limited")
    async def limited():
        raise ProblemDetailError(
            429,
            "Muitas tentativas",
            "Tente novamente mais tarde.",
            headers={"Retry-After": "900"},
        )

    return TestClient(app)


def test_http_error_preserves_bearer_header_and_problem_media_type():
    response = _client().get("/unauthorized")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    )
    assert response.json() == {
        "type": "https://sidebrain.api/errors/401",
        "title": "Erro de autenticação",
        "status": 401,
        "detail": "Credencial de autenticação ausente ou inválida.",
    }


def test_problem_error_preserves_retry_after_without_exposing_secrets():
    response = _client().get("/limited")
    body = response.json()

    assert response.status_code == 429
    assert response.headers["retry-after"] == "900"
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    )
    assert not {"password", "password_hash", "token"} & set(body)
