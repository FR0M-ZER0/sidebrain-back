from fastapi.testclient import TestClient

from main import app
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.track_schema import TrackCreate
from sidebrain_back.services.track_service import get_track_service


def test_track_endpoints_require_authentication():
    client = TestClient(app)

    for method, path in (
        ("post", "/api/v1/tracks"),
        ("get", "/api/v1/tracks/generations/not-a-uuid"),
        ("get", "/api/v1/tracks/generations/not-a-uuid/events"),
        ("get", "/api/v1/tracks"),
        ("get", "/api/v1/tracks/not-a-uuid"),
        ("patch", "/api/v1/tracks/not-a-uuid"),
        ("delete", "/api/v1/tracks/not-a-uuid"),
    ):
        response = client.request(
            method.upper(),
            path,
            json={"title": "Python"} if method in {"post", "patch"} else None,
        )
        assert response.status_code == 401
        assert response.json()["status"] == 401


def test_create_rejects_internal_fields_and_empty_title():
    for payload in (
        {"title": "   "},
        {"title": "Python", "userId": "attacker"},
        {"title": "Python", "id": "attacker"},
    ):
        try:
            TrackCreate.model_validate(payload)
        except ValueError:
            continue
        raise AssertionError("payload inválido aceito")


def test_pagination_empty_response_has_zero_total_pages():
    response = PaginatedResponse.build([], 1, 20, 0)
    assert response.model_dump() == {
        "data": [],
        "page": 1,
        "page_size": 20,
        "total_items": 0,
        "total_pages": 0,
    }


def test_track_list_binds_filters_and_returns_pagination(test_app):
    class ServiceDouble:
        def __init__(self):
            self.params = None

        async def list_tracks(self, _user, params):
            self.params = params
            return PaginatedResponse.build(
                [], params.page, params.page_size, total_items=0
            )

    service = ServiceDouble()
    test_app.dependency_overrides[get_track_service] = lambda: service
    client = TestClient(test_app)
    response = client.get(
        "/api/v1/tracks",
        params={
            "q": " Python ",
            "level": "beginner",
            "has_missions": "false",
            "sort": "oldest",
            "page": 2,
            "page_size": 5,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "data": [],
        "page": 2,
        "page_size": 5,
        "total_items": 0,
        "total_pages": 0,
    }
    assert service.params.q == "Python"
    assert service.params.level.value == "beginner"
    assert service.params.has_missions is False
    assert service.params.sort == "oldest"
