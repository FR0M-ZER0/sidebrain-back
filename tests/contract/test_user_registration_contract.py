from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from sidebrain_back.schemas.auth_schema import AuthResponse
from sidebrain_back.schemas.user_schema import UserResponse
from sidebrain_back.services.auth_errors import ConflictError
from sidebrain_back.services.auth_service import get_auth_service


class RegistrationServiceDouble:
    async def register_user(self, payload):
        if str(payload.email) == "used@example.com":
            raise ConflictError
        return AuthResponse(
            accessToken="header.payload.signature",
            user=UserResponse(
                id=uuid4(),
                name=payload.name,
                email=payload.email,
            ),
        )


@pytest.fixture
def client(test_app):
    test_app.dependency_overrides[get_auth_service] = RegistrationServiceDouble
    return TestClient(test_app)


def test_register_returns_only_public_auth_response(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": " Maria ",
            "email": "MARIA@example.com",
            "password": "12345678",
        },
    )

    assert response.status_code == 201
    assert set(response.json()) == {"accessToken", "tokenType", "user"}
    assert set(response.json()["user"]) == {"id", "name", "email"}
    assert response.json()["tokenType"] == "Bearer"


def test_register_maps_reserved_email_and_rejects_extra_fields(client):
    conflict = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Maria",
            "email": "used@example.com",
            "password": "12345678",
        },
    )
    invalid = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Maria",
            "email": "new@example.com",
            "password": "12345678",
            "usr_is_deleted": False,
        },
    )

    assert conflict.status_code == 409
    assert invalid.status_code == 422
    assert conflict.headers["content-type"].startswith(
        "application/problem+json"
    )
