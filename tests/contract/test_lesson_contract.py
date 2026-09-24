from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.schemas.lesson_schema import LessonResponse
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.services.lesson_service import get_lesson_service


class LessonServiceDouble:
    def __init__(self, *, missing=False, conflict=False) -> None:
        self.missing = missing
        self.conflict = conflict

    @staticmethod
    def _lesson(lesson_id=None, **changes):
        values = {
            "id": lesson_id or uuid4(),
            "title": "Variables",
            "text": "Content",
            "status": LessonStatusEnum.IDLE,
            "position": 1,
            "updated_at": datetime.now(UTC).replace(tzinfo=None),
        }
        values.update(changes)
        return LessonResponse(**values)

    def _raise_if_unavailable(self):
        if self.missing:
            raise ProblemDetailError(
                404, "Não encontrado", "Lição não encontrada."
            )
        if self.conflict:
            raise ProblemDetailError(
                409,
                "Conflito",
                "Já existe uma lição nesta posição para a etapa.",
            )

    async def create_lesson(self, user, step_id, payload):
        self._raise_if_unavailable()
        return self._lesson(
            title=payload.title, text=payload.text, position=payload.position
        )

    async def list_lessons_by_step_id(self, user, step_id, page, page_size):
        self._raise_if_unavailable()
        return PaginatedResponse.build(
            [self._lesson()], page, page_size, total_items=1
        )

    async def get_lesson(self, user, lesson_id):
        self._raise_if_unavailable()
        return self._lesson(lesson_id)

    async def update_lesson(self, user, lesson_id, payload):
        self._raise_if_unavailable()
        return self._lesson(
            lesson_id,
            title=payload.title,
            text=payload.text,
            status=payload.status,
            position=payload.position,
        )

    async def delete_lesson(self, user, lesson_id):
        self._raise_if_unavailable()


@pytest.fixture
def lesson_client(test_app):
    test_app.dependency_overrides[get_lesson_service] = LessonServiceDouble
    return TestClient(test_app)


def assert_public_lesson(body):
    assert set(body) == {
        "id",
        "title",
        "text",
        "status",
        "position",
        "updated_at",
        "feedbacks",
        "files",
        "quizzes",
    }
    assert body["feedbacks"] == body["files"] == body["quizzes"] == []
    assert not any(key.startswith("lsn_") for key in body)
    assert "lesson_files" not in body


def test_create_lesson_returns_201_idle_and_public_empty_collections(
    lesson_client,
):
    response = lesson_client.post(
        f"/api/v1/steps/{uuid4()}/lessons",
        json={"title": " Variables ", "text": " Content ", "position": 1},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "idle"
    assert_public_lesson(response.json())


@pytest.mark.parametrize(
    "extra",
    [
        {"step_id": str(uuid4())},
        {"status": "done"},
        {"id": str(uuid4())},
        {"feedbacks": []},
        {"files": []},
        {"quizzes": []},
        {"updated_at": "2026-01-01T00:00:00"},
        {"is_deleted": False},
    ],
)
def test_create_rejects_managed_fields(lesson_client, extra):
    payload = {"title": "Variables", "text": "Content", "position": 1}
    payload.update(extra)

    response = lesson_client.post(
        f"/api/v1/steps/{uuid4()}/lessons", json=payload
    )

    assert response.status_code == 422
    assert response.json()["status"] == 422


def test_list_lesson_contract_defaults_and_public_files(lesson_client):
    response = lesson_client.get(f"/api/v1/steps/{uuid4()}/lessons")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_items"] == 1
    assert body["total_pages"] == 1
    assert_public_lesson(body["data"][0])


@pytest.mark.parametrize(
    "query", ["page=0", "page_size=0", "page_size=101", "page=x"]
)
def test_list_rejects_invalid_pagination(lesson_client, query):
    response = lesson_client.get(f"/api/v1/steps/{uuid4()}/lessons?{query}")

    assert response.status_code == 422
    assert response.json()["status"] == 422


def test_get_lesson_returns_public_contract(lesson_client):
    lesson_id = uuid4()
    response = lesson_client.get(f"/api/v1/lessons/{lesson_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(lesson_id)
    assert_public_lesson(response.json())


def test_update_requires_all_fields_and_rejects_managed_fields(lesson_client):
    lesson_id = uuid4()
    valid = {
        "title": "Updated",
        "text": "Text",
        "status": "done",
        "position": 2,
    }

    for missing in valid:
        payload = valid.copy()
        payload.pop(missing)
        response = lesson_client.put(
            f"/api/v1/lessons/{lesson_id}", json=payload
        )
        assert response.status_code == 422

    for extra in ("step_id", "id", "feedbacks", "files", "updated_at"):
        payload = valid | {
            extra: [] if extra in {"feedbacks", "files"} else "x"
        }
        response = lesson_client.put(
            f"/api/v1/lessons/{lesson_id}", json=payload
        )
        assert response.status_code == 422


def test_update_returns_200(lesson_client):
    response = lesson_client.put(
        f"/api/v1/lessons/{uuid4()}",
        json={
            "title": "Updated",
            "text": "Text",
            "status": "in_progress",
            "position": 2,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_delete_returns_204_without_body(lesson_client):
    response = lesson_client.delete(f"/api/v1/lessons/{uuid4()}")

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        (
            "post",
            "/api/v1/steps/not-a-uuid/lessons",
            {"title": "A", "text": "B", "position": 1},
        ),
        ("get", "/api/v1/steps/not-a-uuid/lessons", None),
        ("get", "/api/v1/lessons/not-a-uuid", None),
        (
            "put",
            "/api/v1/lessons/not-a-uuid",
            {"title": "A", "text": "B", "status": "idle", "position": 1},
        ),
        ("delete", "/api/v1/lessons/not-a-uuid", None),
    ],
)
def test_lesson_endpoints_reject_invalid_uuid(
    lesson_client, method, path, json
):
    response = lesson_client.request(method.upper(), path, json=json)

    assert response.status_code == 422
    assert response.json()["status"] == 422


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        (
            "post",
            f"/api/v1/steps/{uuid4()}/lessons",
            {"title": "A", "text": "B", "position": 1},
        ),
        ("get", f"/api/v1/steps/{uuid4()}/lessons", None),
        ("get", f"/api/v1/lessons/{uuid4()}", None),
        (
            "put",
            f"/api/v1/lessons/{uuid4()}",
            {"title": "A", "text": "B", "status": "idle", "position": 1},
        ),
        ("delete", f"/api/v1/lessons/{uuid4()}", None),
    ],
)
def test_lesson_endpoints_require_authentication(method, path, json):
    response = TestClient(app).request(method.upper(), path, json=json)

    assert response.status_code == 401
    assert response.json()["status"] == 401


@pytest.mark.parametrize("status_code", [404, 409])
def test_lesson_mutations_return_problem_details(test_app, status_code):
    def service():
        return LessonServiceDouble(
            missing=status_code == 404, conflict=status_code == 409
        )

    test_app.dependency_overrides[get_lesson_service] = service
    response = TestClient(test_app).post(
        f"/api/v1/steps/{uuid4()}/lessons",
        json={"title": "A", "text": "B", "position": 1},
    )

    assert response.status_code == status_code
    assert response.json()["status"] == status_code
    assert set(response.json()) >= {"type", "title", "status", "detail"}
