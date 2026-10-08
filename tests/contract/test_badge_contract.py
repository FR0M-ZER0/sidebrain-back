from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from sidebrain_back.routers.v1.badge_router import router


def test_badge_routes_are_registered_in_v1_router():
    paths = {route.path for route in router.routes}

    assert "/v1/badges" in paths
    assert "/v1/badges/{badge_id}" in paths


def test_badge_routes_are_registered_in_aggregated_application():
    response = TestClient(app).get(f"/api/v1/badges/{uuid4()}")

    assert response.status_code == 401
    assert response.json()["status"] == 401


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
