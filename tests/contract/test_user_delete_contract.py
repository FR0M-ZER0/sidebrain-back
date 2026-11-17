from fastapi.testclient import TestClient

from sidebrain_back.services.auth_errors import ResourceNotFoundError
from sidebrain_back.services.user_service import get_user_service


class DeleteServiceDouble:
    def __init__(self, missing=False):
        self.missing = missing

    async def delete_user(self, user):
        if self.missing:
            raise ResourceNotFoundError


def test_delete_profile_returns_empty_204(test_app):
    test_app.dependency_overrides[get_user_service] = DeleteServiceDouble
    response = TestClient(test_app).delete("/api/v1/users/me")
    assert response.status_code == 204
    assert response.content == b""


def test_delete_profile_maps_late_disappearance_to_404(test_app):
    test_app.dependency_overrides[get_user_service] = lambda: (
        DeleteServiceDouble(missing=True)
    )
    response = TestClient(test_app).delete("/api/v1/users/me")
    assert response.status_code == 404
