from fastapi.testclient import TestClient

from sidebrain_back.schemas.user_schema import UserResponse
from sidebrain_back.services.auth_errors import ConflictError
from sidebrain_back.services.user_service import get_user_service


class UserUpdateServiceDouble:
    async def update_user(self, user, payload):
        if payload.email == "used@example.com":
            raise ConflictError
        values = {
            "id": user.usr_id,
            "name": payload.name or user.usr_name,
            "email": payload.email or user.usr_email,
        }
        return UserResponse(**values)


def test_update_profile_accepts_public_fields(test_app):
    test_app.dependency_overrides[get_user_service] = UserUpdateServiceDouble
    response = TestClient(test_app).put(
        "/api/v1/users/me", json={"name": " Maria Atualizada "}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Maria Atualizada"


def test_update_profile_rejects_empty_and_private_fields(test_app):
    test_app.dependency_overrides[get_user_service] = UserUpdateServiceDouble
    client = TestClient(test_app)
    assert client.put("/api/v1/users/me", json={}).status_code == 422
    assert (
        client.put(
            "/api/v1/users/me", json={"usr_password_hash": "x"}
        ).status_code
        == 422
    )


def test_update_profile_maps_reserved_email_to_conflict(test_app):
    test_app.dependency_overrides[get_user_service] = UserUpdateServiceDouble
    response = TestClient(test_app).put(
        "/api/v1/users/me", json={"email": "used@example.com"}
    )
    assert response.status_code == 409
