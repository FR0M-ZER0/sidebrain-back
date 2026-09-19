import logging
from unittest.mock import patch

import httpx
import pytest
from celery.exceptions import Retry
from groq import APIConnectionError

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.tasks.knowledge_assessment_task import (
    prepare_knowledge_assessment_task,
)

SECRET_USER_ID = "8d4e1d4b-3b0e-4f2d-a5f4-123456789abc"


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

            result = prepare_knowledge_assessment_task.apply(
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


def test_worker_registers_assessment_task_module():
    module = "sidebrain_back.tasks.knowledge_assessment_task"

    assert module in celery_app.conf.include
    celery_app.loader.import_default_modules()
    assert "tasks.prepare_knowledge_assessment" in celery_app.tasks


def test_task_function_name_and_success_log_follow_conventions(caplog):
    assert prepare_knowledge_assessment_task.run.__name__.endswith("_task")

    with (
        patch(
            "sidebrain_back.tasks.knowledge_assessment_task."
            "KnowledgeAssessmentService"
        ) as service_cls,
        caplog.at_level(
            logging.INFO,
            logger="sidebrain_back.tasks.knowledge_assessment_task",
        ),
    ):
        service_cls.return_value.prepare_assessment.return_value = {
            "assessment_id": "ae41d14d-8d7e-4b28-9b88-9d74637f54a7",
            "status": "skipped",
            "level": "beginner",
            "questions": [],
        }

        result = prepare_knowledge_assessment_task.apply(
            args=[SECRET_USER_ID, "secret-subject", None, True]
        )

    assert result.successful() is True
    success = next(
        record
        for record in caplog.records
        if getattr(record, "event", None)
        == "knowledge_assessment_succeeded"
    )
    assert success.task_id is not None
    assert success.attempt == 1
    assert SECRET_USER_ID not in caplog.text
    assert "secret-subject" not in caplog.text


def test_task_logs_retry_without_sensitive_content(caplog):
    error = APIConnectionError(
        message="secret provider error",
        request=httpx.Request("POST", "https://provider.invalid"),
    )
    prepare_knowledge_assessment_task.push_request(
        id="task-retry-id",
        retries=1,
    )
    try:
        with (
            patch(
                "sidebrain_back.tasks.knowledge_assessment_task."
                "KnowledgeAssessmentService"
            ) as service_cls,
            patch.object(
                prepare_knowledge_assessment_task,
                "retry",
                side_effect=Retry(),
            ),
            caplog.at_level(
                logging.WARNING,
                logger="sidebrain_back.tasks.knowledge_assessment_task",
            ),
            pytest.raises(Retry),
        ):
            service_cls.return_value.prepare_assessment.side_effect = error
            prepare_knowledge_assessment_task.run(
                SECRET_USER_ID,
                "secret-subject",
            )
    finally:
        prepare_knowledge_assessment_task.pop_request()

    retry_log = next(
        record
        for record in caplog.records
        if getattr(record, "event", None)
        == "knowledge_assessment_retry_scheduled"
    )
    assert retry_log.task_id == "task-retry-id"
    assert retry_log.attempt == 2
    assert retry_log.exception_type == "APIConnectionError"
    assert "secret provider error" not in caplog.text
    assert SECRET_USER_ID not in caplog.text
    assert "secret-subject" not in caplog.text


def test_task_logs_definitive_failure_without_sensitive_content(caplog):
    prepare_knowledge_assessment_task.push_request(
        id="task-failure-id",
        retries=0,
    )
    try:
        with (
            patch(
                "sidebrain_back.tasks.knowledge_assessment_task."
                "KnowledgeAssessmentService"
            ) as service_cls,
            caplog.at_level(
                logging.ERROR,
                logger="sidebrain_back.tasks.knowledge_assessment_task",
            ),
            pytest.raises(ValueError, match="secret invalid response"),
        ):
            service_cls.return_value.prepare_assessment.side_effect = (
                ValueError("secret invalid response")
            )
            prepare_knowledge_assessment_task.run(
                SECRET_USER_ID,
                "secret-subject",
            )
    finally:
        prepare_knowledge_assessment_task.pop_request()

    failure_log = next(
        record
        for record in caplog.records
        if getattr(record, "event", None)
        == "knowledge_assessment_failed"
    )
    assert failure_log.task_id == "task-failure-id"
    assert failure_log.attempt == 1
    assert failure_log.exception_type == "ValueError"
    assert "secret invalid response" not in caplog.text
    assert SECRET_USER_ID not in caplog.text
    assert "secret-subject" not in caplog.text
