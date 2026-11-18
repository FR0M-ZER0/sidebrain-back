from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from sidebrain_back.routers.v1.auth_router import get_current_user
from sidebrain_back.services.job_update_service import get_job_update_service


def test_ws_ticket_returns_no_store(authenticated_user):
    service = AsyncMock()
    service.issue_ticket.return_value = "temporary-ticket"
    app.dependency_overrides[get_current_user] = lambda: authenticated_user
    app.dependency_overrides[get_job_update_service] = lambda: service
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.post(
                "/api/v1/auth/ws-ticket",
                json={
                    "channel": "assessment",
                    "resource_id": str(uuid4()),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ticket": "temporary-ticket"}
    assert response.headers["cache-control"] == "no-store"


def test_ws_ticket_validates_resource_before_service(authenticated_user):
    service = AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: authenticated_user
    app.dependency_overrides[get_job_update_service] = lambda: service
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.post(
                "/api/v1/auth/ws-ticket",
                json={"channel": "assessment", "resource_id": "invalid"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    )
    service.issue_ticket.assert_not_awaited()
