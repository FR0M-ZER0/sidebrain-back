from unittest.mock import patch

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.tasks.knowledge_assessment_task import (
    prepare_knowledge_assessment,
)


def test_task_returns_skip_result_without_provider_call():
    original = celery_app.conf.task_always_eager
    celery_app.conf.task_always_eager = True
    try:
        with patch(
            "sidebrain_back.tasks.knowledge_assessment_task.KnowledgeAssessmentService"
        ) as service_cls:
            service = service_cls.return_value
            service.prepare_assessment.return_value = {
                "assessment_id": "ae41d14d-8d7e-4b28-9b88-9d74637f54a7",
                "status": "skipped",
                "level": "beginner",
                "questions": [],
            }

            result = prepare_knowledge_assessment.apply(
                args=[
                    "8d4e1d4b-3b0e-4f2d-a5f4-123456789abc",
                    "Python",
                    "Aprender FastAPI",
                    True,
                ]
            )

        assert result.successful() is True
        payload = result.get()
        assert payload["status"] == "skipped"
        assert payload["level"] == "beginner"
        assert payload["questions"] == []
    finally:
        celery_app.conf.task_always_eager = original
