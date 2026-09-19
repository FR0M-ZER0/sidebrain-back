from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from sidebrain_back.routers.v1.feedback_router import router
from sidebrain_back.schemas.feedback_schema import (
    FeedbackCreate,
    FeedbackUpdate,
)


def test_feedback_routes_are_registered_under_api_v1():
    paths = {route.path for route in router.routes}

    assert "/v1/lessons/{lesson_id}/feedbacks" in paths
    assert "/v1/feedbacks/{feedback_id}" in paths


def test_feedback_routes_are_registered_in_aggregated_application():
    response = TestClient(app).get(f"/api/v1/feedbacks/{uuid4()}")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "   "},
        {"text": "ok", "author_id": str(uuid4())},
        {"text": "ok", "fbk_is_deleted": False},
    ],
)
def test_feedback_create_rejects_empty_and_internal_fields(payload):
    with pytest.raises(ValueError):
        FeedbackCreate.model_validate(payload)


def test_feedback_update_requires_text_and_normalizes_it():
    assert FeedbackUpdate(text="  claro  ").text == "claro"
    with pytest.raises(ValueError):
        FeedbackUpdate.model_validate({})
