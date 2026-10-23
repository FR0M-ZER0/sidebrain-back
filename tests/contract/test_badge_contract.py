from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from sidebrain_back.routers.v1.badge_router import router
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.services.badge_service import get_badge_service


def test_badge_routes_are_registered_in_v1_router():
    paths = {route.path for route in router.routes}

    assert "/v1/badges" in paths
    assert "/v1/badges/{badge_id}" in paths
    assert "/v1/badges/recalculate-progress" in paths


def test_badge_routes_are_registered_in_aggregated_application():
    response = TestClient(app).get(f"/api/v1/badges/{uuid4()}")

    assert response.status_code == 401
    assert response.json()["status"] == 401


def test_badge_progress_recalculation_requires_authentication():
    response = TestClient(app).post("/api/v1/badges/recalculate-progress")
    assert response.status_code == 401
    assert response.json()["status"] == 401


def test_badge_list_filters_require_authentication():
    response = TestClient(app).get(
        "/api/v1/badges", params={"status": "done", "rarity": "rare"}
    )
    assert response.status_code == 401
    assert response.json()["status"] == 401


def test_badge_list_binds_filters_and_returns_pagination(test_app):
    class ServiceDouble:
        def __init__(self):
            self.params = None

        async def list_badges(self, _user, params):
            self.params = params
            return PaginatedResponse.build(
                [], params.page, params.page_size, total_items=0
            )

    service = ServiceDouble()
    test_app.dependency_overrides[get_badge_service] = lambda: service
    with TestClient(test_app) as client:
        response = client.get(
            "/api/v1/badges",
            params={
                "status": "in_progress",
                "rarity": "rare",
                "criteria": "day_streak",
                "q": "Python",
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
    assert service.params.status.value == "in_progress"
    assert service.params.rarity.value == "rare"
    assert service.params.criteria.value == "day_streak"
    assert service.params.q == "Python"
    assert service.params.sort == "oldest"


def test_badge_create_rejects_invalid_public_payload_without_authentication():
    response = TestClient(app).post(
        "/api/v1/badges",
        json={
            "name": "Badge",
            "description": None,
            "rarity": "common",
            "criteria": "xp_gained",
            "criteria_value": 1,
            "bdg_is_deleted": False,
        },
    )

    assert response.status_code == 401
