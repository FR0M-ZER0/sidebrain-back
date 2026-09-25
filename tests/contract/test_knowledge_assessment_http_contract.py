from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentAcceptedResponse,
    AssessmentDetail,
)
from sidebrain_back.services.knowledge_assessment_service import (
    get_knowledge_assessment_service,
)


def _detail_for_status(assessment_id, assessment_status):
    now = datetime.now(UTC).replace(tzinfo=None)
    has_questions = assessment_status in {
        KnowledgeAssessmentStatusEnum.GENERATED,
        KnowledgeAssessmentStatusEnum.COMPLETED,
    }
    return AssessmentDetail.model_validate(
        {
            "assessment_id": assessment_id,
            "subject": "Python",
            "objective": "FastAPI",
            "skip": assessment_status is KnowledgeAssessmentStatusEnum.SKIPPED,
            "status": assessment_status,
            "questions": (
                [
                    {
                        "id": str(uuid4()),
                        "statement": f"Pergunta {index}",
                        "alternatives": [
                            {
                                "id": str(uuid4()),
                                "text": f"Alternativa {item}",
                            }
                            for item in range(1, 5)
                        ],
                    }
                    for index in range(1, 6)
                ]
                if has_questions
                else []
            ),
            "score": (
                4
                if assessment_status is KnowledgeAssessmentStatusEnum.COMPLETED
                else None
            ),
            "level": (
                "advanced"
                if assessment_status is KnowledgeAssessmentStatusEnum.COMPLETED
                else (
                    "beginner"
                    if assessment_status
                    is KnowledgeAssessmentStatusEnum.SKIPPED
                    else None
                )
            ),
            "error_code": (
                "generation_failed"
                if assessment_status is KnowledgeAssessmentStatusEnum.FAILED
                else None
            ),
            "created_at": now,
            "updated_at": now,
            "completed_at": (
                now
                if assessment_status
                in {
                    KnowledgeAssessmentStatusEnum.SKIPPED,
                    KnowledgeAssessmentStatusEnum.COMPLETED,
                }
                else None
            ),
        }
    )


class AssessmentHttpService:
    def __init__(
        self,
        status: KnowledgeAssessmentStatusEnum = (
            KnowledgeAssessmentStatusEnum.PENDING
        ),
        error: ProblemDetailError | None = None,
    ) -> None:
        self.assessment_id = uuid4()
        self.status = status
        self.error = error

    async def create_knowledge_assessment(self, _user, _payload):
        if self.error is not None:
            raise self.error
        return AssessmentAcceptedResponse(
            assessment_id=self.assessment_id,
            status=self.status,
        )

    async def submit_knowledge_assessment_answers(
        self, _user, assessment_id, _payload
    ):
        if self.error is not None:
            raise self.error
        return _detail_for_status(
            assessment_id, KnowledgeAssessmentStatusEnum.COMPLETED
        )

    async def get_knowledge_assessment(self, _user, assessment_id):
        if self.error is not None:
            raise self.error
        return _detail_for_status(assessment_id, self.status)


@pytest.mark.parametrize(
    "assessment_status,expected_status",
    [
        (KnowledgeAssessmentStatusEnum.PENDING, 202),
        (KnowledgeAssessmentStatusEnum.GENERATED, 200),
    ],
)
def test_create_assessment_returns_location_and_state_specific_status(
    test_app, assessment_status, expected_status
):
    service = AssessmentHttpService(assessment_status)
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: service
    )

    response = TestClient(test_app).post(
        "/api/v1/assessments",
        json={
            "subject": "  Python  ",
            "objective": "  FastAPI  ",
            "skip": False,
        },
    )

    assert response.status_code == expected_status
    assert response.headers["location"] == (
        f"/api/v1/assessments/{service.assessment_id}"
    )
    assert response.json() == {
        "assessment_id": str(service.assessment_id),
        "status": assessment_status.value,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"subject": "   "},
        {"subject": "x" * 256},
        {"subject": "Python", "objective": "   "},
        {"subject": "Python", "objective": "x" * 1001},
        {"subject": "Python", "user_id": str(uuid4())},
        {"subject": "Python", "status": "generated"},
    ],
)
def test_create_assessment_rejects_invalid_or_extra_fields(test_app, payload):
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: AssessmentHttpService()
    )

    response = TestClient(test_app).post(
        "/api/v1/assessments",
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["status"] == 422
    assert response.json()["type"].endswith("/422")


def test_create_assessment_requires_authentication():
    response = TestClient(app).post(
        "/api/v1/assessments",
        json={"subject": "Python"},
    )

    assert response.status_code == 401
    assert response.json()["status"] == 401


def test_publish_failure_uses_problem_details_503(test_app):
    service = AssessmentHttpService(
        error=ProblemDetailError(
            503,
            "Serviço indisponível",
            "Não foi possível iniciar a avaliação.",
            error_code="generation_failed",
        )
    )
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: service
    )

    response = TestClient(test_app).post(
        "/api/v1/assessments",
        json={"subject": "Python"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "type": "https://sidebrain.api/errors/503",
        "title": "Serviço indisponível",
        "status": 503,
        "detail": "Não foi possível iniciar a avaliação.",
        "error_code": "generation_failed",
    }


def _answers_payload():
    return {
        "answers": [
            {
                "question_id": str(uuid4()),
                "alternative_id": str(uuid4()),
            }
            for _ in range(5)
        ]
    }


def _duplicate_answers_payload():
    payload = _answers_payload()
    payload["answers"][-1]["question_id"] = payload["answers"][0][
        "question_id"
    ]
    return payload


def test_submit_answers_returns_completed_without_answer_key(test_app):
    service = AssessmentHttpService()
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: service
    )

    response = TestClient(test_app).post(
        f"/api/v1/assessments/{uuid4()}/answers",
        json=_answers_payload(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["score"] == 4
    assert response.json()["level"] == "advanced"
    serialized = response.text
    assert "is_correct" not in serialized
    assert "correct_alternative_id" not in serialized


@pytest.mark.parametrize(
    "status_code,title,error_code",
    [
        (404, "Não encontrado", None),
        (409, "Conflito", "assessment_not_generated"),
        (500, "Erro interno", None),
    ],
)
def test_submit_answers_maps_service_errors_to_problem_details(
    test_app, status_code, title, error_code
):
    service = AssessmentHttpService(
        error=ProblemDetailError(
            status_code,
            title,
            "Mensagem pública.",
            error_code=error_code,
        )
    )
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: service
    )

    response = TestClient(test_app).post(
        f"/api/v1/assessments/{uuid4()}/answers",
        json=_answers_payload(),
    )

    assert response.status_code == status_code
    assert response.json()["status"] == status_code
    assert response.json()["title"] == title


@pytest.mark.parametrize(
    "payload",
    [
        {"answers": []},
        {"answers": _answers_payload()["answers"][:4]},
        _duplicate_answers_payload(),
        {**_answers_payload(), "score": 5},
    ],
)
def test_submit_answers_rejects_cardinality_duplicates_and_extras(
    test_app, payload
):
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: AssessmentHttpService()
    )

    response = TestClient(test_app).post(
        f"/api/v1/assessments/{uuid4()}/answers",
        json=payload,
    )

    assert response.status_code == 422
    assert response.json()["status"] == 422


def test_skip_flow_is_pending_then_skipped_and_rejects_answers(test_app):
    pending_service = AssessmentHttpService()
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: pending_service
    )
    create_response = TestClient(test_app).post(
        "/api/v1/assessments",
        json={"subject": "Álgebra", "skip": True},
    )
    assessment_id = create_response.json()["assessment_id"]

    assert create_response.status_code == 202
    assert create_response.json()["status"] == "pending"

    skipped_service = AssessmentHttpService(
        KnowledgeAssessmentStatusEnum.SKIPPED
    )
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: skipped_service
    )
    get_response = TestClient(test_app).get(
        f"/api/v1/assessments/{assessment_id}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "skipped"
    assert get_response.json()["level"] == "beginner"
    assert get_response.json()["score"] is None
    assert get_response.json()["questions"] == []

    skipped_service.error = ProblemDetailError(
        409,
        "Conflito",
        "A avaliação não está disponível para submissão.",
        error_code="assessment_not_generated",
    )
    answer_response = TestClient(test_app).post(
        f"/api/v1/assessments/{assessment_id}/answers",
        json=_answers_payload(),
    )
    assert answer_response.status_code == 409


@pytest.mark.parametrize(
    "assessment_status,question_count,score,level,error_code",
    [
        (KnowledgeAssessmentStatusEnum.PENDING, 0, None, None, None),
        (KnowledgeAssessmentStatusEnum.GENERATED, 5, None, None, None),
        (
            KnowledgeAssessmentStatusEnum.SKIPPED,
            0,
            None,
            "beginner",
            None,
        ),
        (
            KnowledgeAssessmentStatusEnum.COMPLETED,
            5,
            4,
            "advanced",
            None,
        ),
        (
            KnowledgeAssessmentStatusEnum.FAILED,
            0,
            None,
            None,
            "generation_failed",
        ),
    ],
)
def test_get_assessment_projects_each_public_state(
    test_app,
    assessment_status,
    question_count,
    score,
    level,
    error_code,
):
    service = AssessmentHttpService(assessment_status)
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: service
    )

    response = TestClient(test_app).get(
        f"/api/v1/assessments/{service.assessment_id}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == assessment_status.value
    assert len(body["questions"]) == question_count
    assert body["score"] == score
    assert body["level"] == level
    assert body["error_code"] == error_code
    for forbidden in (
        "is_correct",
        "correct_alternative_id",
        "user_id",
        "task_id",
        "retry",
        "provider_error",
        "exception",
    ):
        assert forbidden not in response.text


def test_get_assessment_returns_identical_404_for_missing_and_unowned(
    test_app,
):
    error = ProblemDetailError(
        404,
        "Não encontrado",
        "Avaliação não encontrada.",
    )
    service = AssessmentHttpService(error=error)
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: service
    )

    first = TestClient(test_app).get(f"/api/v1/assessments/{uuid4()}")
    second = TestClient(test_app).get(f"/api/v1/assessments/{uuid4()}")

    assert first.status_code == second.status_code == 404
    assert first.json() == second.json()


def test_get_assessment_rejects_invalid_uuid(test_app):
    test_app.dependency_overrides[get_knowledge_assessment_service] = (
        lambda: AssessmentHttpService()
    )

    response = TestClient(test_app).get(
        "/api/v1/assessments/not-a-uuid"
    )

    assert response.status_code == 422
    assert response.json()["status"] == 422


def test_get_assessment_requires_authentication():
    response = TestClient(app).get(f"/api/v1/assessments/{uuid4()}")

    assert response.status_code == 401
    assert response.json()["status"] == 401
