from fastapi.testclient import TestClient

from main import app
from sidebrain_back.schemas.step_schema import StepCreate
from sidebrain_back.schemas.track_schema import (
    LessonResponse as HierarchyLessonResponse,
)


def test_step_hierarchy_preserves_historical_lesson_files_name():
    assert "lesson_files" in HierarchyLessonResponse.model_fields
    assert "files" not in HierarchyLessonResponse.model_fields


def test_step_endpoints_require_authentication():
    client = TestClient(app)

    for method, path in (
        ("post", "/api/v1/tracks/not-a-uuid/steps"),
        ("get", "/api/v1/tracks/not-a-uuid/steps"),
        ("get", "/api/v1/tracks/not-a-uuid/steps/not-a-uuid"),
        ("put", "/api/v1/tracks/not-a-uuid/steps/not-a-uuid"),
        ("delete", "/api/v1/tracks/not-a-uuid/steps/not-a-uuid"),
    ):
        response = client.request(
            method.upper(),
            path,
            json={"level": "beginner", "title": "Intro"}
            if method in {"post", "put"}
            else None,
        )
        assert response.status_code == 401
        assert response.json()["status"] == 401


def test_step_payload_rejects_managed_fields():
    try:
        StepCreate(level="beginner", title="Intro", track_id="attacker")
    except ValueError:
        return
    raise AssertionError("payload inválido aceito")


def test_step_pagination_rejects_invalid_bounds():
    client = TestClient(app)

    response = client.get(
        "/api/v1/tracks/not-a-uuid/steps?page=0&page_size=101"
    )

    assert response.status_code == 401
