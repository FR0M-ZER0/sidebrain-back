import pytest
from fastapi.testclient import TestClient

from sidebrain_back.core.rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
)
from sidebrain_back.services.auth_errors import (
    AuthenticationError,
    DomainValidationError,
    ResourceNotFoundError,
)
from sidebrain_back.services.user_service import get_user_service


class PasswordServiceDouble:
    async def update_password(self, user, payload, origin):
        if payload.current_password == "incorreta":
            raise AuthenticationError
        if payload.current_password == "bloqueada":
            raise RateLimitExceeded(120)
        if payload.current_password == "redis-offline":
            raise RateLimitUnavailable
        if payload.current_password == "sem-conta":
            raise ResourceNotFoundError
        if payload.current_password == payload.new_password:
            raise DomainValidationError("A nova senha deve ser diferente.")


def test_password_change_returns_empty_204(test_app):
    test_app.dependency_overrides[get_user_service] = PasswordServiceDouble
    response = TestClient(test_app).put(
        "/api/v1/users/me/password",
        json={
            "currentPassword": "senha-antiga",
            "newPassword": "senha-nova-123",
        },
    )
    assert response.status_code == 204
    assert response.content == b""


def test_password_change_validates_payload_and_current_password(test_app):
    test_app.dependency_overrides[get_user_service] = PasswordServiceDouble
    client = TestClient(test_app)
    wrong = client.put(
        "/api/v1/users/me/password",
        json={"currentPassword": "incorreta", "newPassword": "12345678"},
    )
    short = client.put(
        "/api/v1/users/me/password",
        json={"currentPassword": "antiga", "newPassword": "curta"},
    )
    assert wrong.status_code == 401
    assert short.status_code == 422


@pytest.mark.parametrize(
    ("current", "new", "status"),
    [
        ("bloqueada", "senha-nova", 429),
        ("redis-offline", "senha-nova", 503),
        ("sem-conta", "senha-nova", 404),
        ("senha-igual", "senha-igual", 422),
    ],
)
def test_password_change_maps_domain_failures(
    test_app,
    current,
    new,
    status,
):
    test_app.dependency_overrides[get_user_service] = PasswordServiceDouble
    response = TestClient(test_app).put(
        "/api/v1/users/me/password",
        json={"currentPassword": current, "newPassword": new},
    )
    assert response.status_code == status
    if status == 429:
        assert response.headers["retry-after"] == "120"
