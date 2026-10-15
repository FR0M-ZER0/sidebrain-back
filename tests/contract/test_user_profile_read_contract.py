from fastapi.testclient import TestClient

from sidebrain_back.schemas.user_schema import UserResponse
from sidebrain_back.services.auth_errors import ResourceNotFoundError
from sidebrain_back.services.user_service import get_user_service


class UserReadServiceDouble:
    def __init__(self, missing=False):
        self.missing = missing

    async def get_user(self, user):
        if self.missing:
            raise ResourceNotFoundError
        return UserResponse.model_validate(user)


def test_get_profile_returns_only_public_fields(test_app):
    test_app.dependency_overrides[get_user_service] = UserReadServiceDouble
    response = TestClient(test_app).get("/api/v1/users/me")
    assert response.status_code == 200
    assert set(response.json()) == {"id", "name", "email"}


def test_get_profile_maps_late_disappearance_to_404(test_app):
    test_app.dependency_overrides[get_user_service] = lambda: (
        UserReadServiceDouble(missing=True)
    )
    response = TestClient(test_app).get("/api/v1/users/me")
    assert response.status_code == 404
