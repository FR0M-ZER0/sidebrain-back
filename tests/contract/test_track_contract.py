from fastapi.testclient import TestClient

from main import app
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.track_schema import TrackCreate


def test_track_endpoints_require_authentication():
    client = TestClient(app)

    for method, path in (
        ("post", "/api/v1/tracks"),
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
