from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from sidebrain_back.core.rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
)
from sidebrain_back.schemas.auth_schema import AuthResponse
from sidebrain_back.schemas.user_schema import UserResponse
from sidebrain_back.services.auth_errors import AuthenticationError
from sidebrain_back.services.auth_service import get_auth_service


class LoginServiceDouble:
    async def login_user(self, payload, origin):
        if str(payload.email) == "wrong@example.com":
            raise AuthenticationError
        if str(payload.email) == "limited@example.com":
            raise RateLimitExceeded(321)
        if str(payload.email) == "redis@example.com":
            raise RateLimitUnavailable
        return AuthResponse(
            accessToken="header.payload.signature",
            user=UserResponse(id=uuid4(), name="Maria", email=payload.email),
        )


@pytest.fixture
def client(test_app):
    test_app.dependency_overrides[get_auth_service] = LoginServiceDouble
    return TestClient(test_app)


def test_login_returns_public_auth_response(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": " Maria@Example.com ", "password": "12345678"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "maria@example.com"


@pytest.mark.parametrize(
    ("email", "status"),
    [
        ("wrong@example.com", 401),
        ("limited@example.com", 429),
        ("redis@example.com", 503),
    ],
)
def test_login_maps_domain_failures(client, email, status):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "12345678"},
    )
    assert response.status_code == status
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    )
    if status == 429:
        assert response.headers["retry-after"] == "321"
