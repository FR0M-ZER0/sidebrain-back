from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.schemas.pagination_schema import PaginatedResponse
from sidebrain_back.schemas.quiz_schema import AnswerResponse, QuizResponse
from sidebrain_back.services.quiz_service import get_quiz_service


class CreateQuizService:
    def __init__(self, *, missing: bool = False) -> None:
        self.missing = missing

    async def create_quiz(self, user, lesson_id, payload):
        if self.missing:
            raise ProblemDetailError(
                404,
                "Não encontrado",
                "Aula não encontrada.",
            )
        return QuizResponse(
            id=uuid4(),
            lesson_id=lesson_id,
            question=payload.question,
        )

    async def list_quizzes_by_lesson(
        self,
        user,
        lesson_id,
        page,
        page_size,
    ):
        quiz = self._quiz(lesson_id)
        return PaginatedResponse.build([quiz], page, page_size, 1)

    async def get_quiz(self, user, quiz_id):
        if self.missing:
            raise ProblemDetailError(
                404,
                "Não encontrado",
                "Quiz não encontrado.",
            )
        quiz = self._quiz(uuid4())
        return quiz.model_copy(update={"id": quiz_id})

    async def update_quiz(self, user, quiz_id, payload):
        quiz = await self.get_quiz(user, quiz_id)
        return quiz.model_copy(update={"question": payload.question})

    async def delete_quiz(self, user, quiz_id):
        await self.get_quiz(user, quiz_id)

    @staticmethod
    def _quiz(lesson_id):
        return QuizResponse(
            id=uuid4(),
            lesson_id=lesson_id,
            question="Question",
            answers=[
                AnswerResponse(
                    id=uuid4(),
                    user_id=uuid4(),
                    text="Answer",
                    rate=AnswerRateEnum.PERFECT,
                )
            ],
        )


def test_create_quiz_returns_public_contract(test_app):
    test_app.dependency_overrides[get_quiz_service] = CreateQuizService
    lesson_id = uuid4()

    response = TestClient(test_app).post(
        f"/api/v1/lessons/{lesson_id}/quizzes",
        json={"question": "  What is a variable?  "},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "lesson_id": str(lesson_id),
        "question": "What is a variable?",
        "answers": [],
    }


def test_create_quiz_requires_authentication():
    response = TestClient(app).post(
        f"/api/v1/lessons/{uuid4()}/quizzes",
        json={"question": "Question"},
    )

    assert response.status_code == 401
    assert response.json()["status"] == 401


@pytest.mark.parametrize(
    "path_id,payload",
    [
        ("not-a-uuid", {"question": "Question"}),
        (str(uuid4()), {}),
        (str(uuid4()), {"question": "   "}),
        (str(uuid4()), {"question": "x" * 1001}),
        (str(uuid4()), {"question": "Question", "lesson_id": str(uuid4())}),
        (str(uuid4()), {"question": "Question", "id": str(uuid4())}),
        (str(uuid4()), {"question": "Question", "answers": []}),
        (str(uuid4()), {"question": "Question", "qui_updated_at": "now"}),
        (str(uuid4()), {"question": "Question", "qui_is_deleted": False}),
    ],
)
def test_create_quiz_rejects_invalid_request(test_app, path_id, payload):
    test_app.dependency_overrides[get_quiz_service] = CreateQuizService

    response = TestClient(test_app).post(
        f"/api/v1/lessons/{path_id}/quizzes",
        json=payload,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == 422
    assert set(body) >= {"type", "title", "status", "detail", "errors"}


def test_create_quiz_conceals_missing_hierarchy(test_app):
    def missing_quiz_service() -> CreateQuizService:
        return CreateQuizService(missing=True)

    test_app.dependency_overrides[get_quiz_service] = missing_quiz_service

    response = TestClient(test_app).post(
        f"/api/v1/lessons/{uuid4()}/quizzes",
        json={"question": "Question"},
    )

    assert response.status_code == 404
    assert response.json()["status"] == 404


def test_list_quizzes_returns_paginated_public_contract(test_app):
    test_app.dependency_overrides[get_quiz_service] = CreateQuizService

    response = TestClient(test_app).get(
        f"/api/v1/lessons/{uuid4()}/quizzes?page=2&page_size=10"
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "data",
        "page",
        "page_size",
        "total_items",
        "total_pages",
    }
    assert (body["page"], body["page_size"]) == (2, 10)
    quiz = body["data"][0]
    assert set(quiz) == {"id", "lesson_id", "question", "answers"}
    assert set(quiz["answers"][0]) == {"id", "user_id", "text", "rate"}
    assert quiz["answers"][0]["rate"] == "perfect"


def test_get_quiz_returns_public_contract(test_app):
    test_app.dependency_overrides[get_quiz_service] = CreateQuizService
    quiz_id = uuid4()

    response = TestClient(test_app).get(f"/api/v1/quizzes/{quiz_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(quiz_id)
    assert set(body) == {"id", "lesson_id", "question", "answers"}
    assert set(body["answers"][0]) == {"id", "user_id", "text", "rate"}


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/lessons/not-a-uuid/quizzes",
        f"/api/v1/lessons/{uuid4()}/quizzes?page=0",
        f"/api/v1/lessons/{uuid4()}/quizzes?page_size=0",
        f"/api/v1/lessons/{uuid4()}/quizzes?page_size=101",
        "/api/v1/quizzes/not-a-uuid",
    ],
)
def test_read_quiz_rejects_invalid_path_or_pagination(test_app, path):
    test_app.dependency_overrides[get_quiz_service] = CreateQuizService

    response = TestClient(test_app).get(path)

    assert response.status_code == 422
    assert response.json()["status"] == 422


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/lessons/{uuid4()}/quizzes",
        f"/api/v1/quizzes/{uuid4()}",
    ],
)
def test_read_quiz_requires_authentication(path):
    response = TestClient(app).get(path)

    assert response.status_code == 401
    assert response.json()["status"] == 401


def test_update_quiz_returns_public_contract_and_preserves_answers(test_app):
    test_app.dependency_overrides[get_quiz_service] = CreateQuizService
    quiz_id = uuid4()

    response = TestClient(test_app).put(
        f"/api/v1/quizzes/{quiz_id}",
        json={"question": "  Updated question  "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(quiz_id)
    assert body["question"] == "Updated question"
    assert len(body["answers"]) == 1
    assert set(body) == {"id", "lesson_id", "question", "answers"}


def test_delete_quiz_returns_empty_204(test_app):
    test_app.dependency_overrides[get_quiz_service] = CreateQuizService

    response = TestClient(test_app).delete(f"/api/v1/quizzes/{uuid4()}")

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": "   "},
        {"question": "x" * 1001},
        {"question": "Question", "lesson_id": str(uuid4())},
        {"question": "Question", "answers": []},
        {"question": "Question", "id": str(uuid4())},
        {"question": "Question", "qui_updated_at": "now"},
        {"question": "Question", "qui_is_deleted": False},
    ],
)
def test_update_quiz_rejects_invalid_payload(test_app, payload):
    test_app.dependency_overrides[get_quiz_service] = CreateQuizService

    response = TestClient(test_app).put(
        f"/api/v1/quizzes/{uuid4()}",
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["status"] == 422


@pytest.mark.parametrize("method", ["put", "delete"])
def test_mutation_rejects_invalid_quiz_uuid(test_app, method):
    test_app.dependency_overrides[get_quiz_service] = CreateQuizService

    response = TestClient(test_app).request(
        method.upper(),
        "/api/v1/quizzes/not-a-uuid",
        json={"question": "Question"} if method == "put" else None,
    )

    assert response.status_code == 422
    assert response.json()["status"] == 422


@pytest.mark.parametrize("method", ["put", "delete"])
def test_mutation_requires_authentication(method):
    response = TestClient(app).request(
        method.upper(),
        f"/api/v1/quizzes/{uuid4()}",
        json={"question": "Question"} if method == "put" else None,
    )

    assert response.status_code == 401
    assert response.json()["status"] == 401


@pytest.mark.parametrize("method", ["put", "delete"])
def test_mutation_conceals_unavailable_quiz(test_app, method):
    def missing_quiz_service() -> CreateQuizService:
        return CreateQuizService(missing=True)

    test_app.dependency_overrides[get_quiz_service] = missing_quiz_service

    response = TestClient(test_app).request(
        method.upper(),
        f"/api/v1/quizzes/{uuid4()}",
        json={"question": "Question"} if method == "put" else None,
    )

    assert response.status_code == 404
    assert response.json()["status"] == 404
