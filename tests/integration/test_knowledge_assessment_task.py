import logging
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from celery.exceptions import Retry
from groq import APIConnectionError, APITimeoutError, RateLimitError
from sqlalchemy import delete

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.core.database import async_session, engine
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.knowledge_assessment_repository import (
    KnowledgeAssessmentRepository,
)
from sidebrain_back.tasks.knowledge_assessment_task import (
    _process_v2,
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
        if getattr(record, "event", None) == "knowledge_assessment_succeeded"
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
        if getattr(record, "event", None) == "knowledge_assessment_failed"
    )
    assert failure_log.task_id == "task-failure-id"
    assert failure_log.attempt == 1
    assert failure_log.exception_type == "ValueError"
    assert "secret invalid response" not in caplog.text
    assert SECRET_USER_ID not in caplog.text
    assert "secret-subject" not in caplog.text


def test_v2_task_preserves_canonical_id_and_returns_minimum_result():
    assessment_id = "ae41d14d-8d7e-4b28-9b88-9d74637f54a7"
    with patch(
        "sidebrain_back.tasks.knowledge_assessment_task._execute_v2",
        return_value={
            "assessment_id": assessment_id,
            "status": "generated",
        },
    ) as execute:
        result = prepare_knowledge_assessment_task.run(
            contract_version=2,
            assessment_id=assessment_id,
            user_id=SECRET_USER_ID,
            subject="secret-subject",
            objective="secret-objective",
            skip=False,
        )

    assert result == {
        "assessment_id": assessment_id,
        "status": "generated",
    }
    execute.assert_called_once_with(
        assessment_id=assessment_id,
        user_id=SECRET_USER_ID,
        subject="secret-subject",
        objective="secret-objective",
        skip=False,
    )


def _transient_errors():
    request = httpx.Request("POST", "https://provider.invalid")
    response = httpx.Response(429, request=request)
    return (
        APIConnectionError(message="secret", request=request),
        APITimeoutError(request=request),
        RateLimitError(
            "secret",
            response=response,
            body=None,
        ),
    )


@pytest.mark.parametrize("error", _transient_errors())
@pytest.mark.parametrize("retries,countdown", [(0, 1), (1, 2), (2, 4)])
def test_v2_transient_errors_use_exact_retry_schedule(
    error, retries, countdown
):
    assessment_id = "ae41d14d-8d7e-4b28-9b88-9d74637f54a7"
    prepare_knowledge_assessment_task.push_request(
        id="task-retry-id",
        retries=retries,
    )
    try:
        with (
            patch(
                "sidebrain_back.tasks.knowledge_assessment_task._execute_v2",
                side_effect=error,
            ),
            patch.object(
                prepare_knowledge_assessment_task,
                "retry",
                side_effect=Retry(),
            ) as retry,
            pytest.raises(Retry),
        ):
            prepare_knowledge_assessment_task.run(
                contract_version=2,
                assessment_id=assessment_id,
                user_id=SECRET_USER_ID,
                subject="secret-subject",
            )
    finally:
        prepare_knowledge_assessment_task.pop_request()

    assert retry.call_args.kwargs["countdown"] == countdown


def test_v2_retry_exhaustion_marks_failed_without_partial_result():
    assessment_id = "ae41d14d-8d7e-4b28-9b88-9d74637f54a7"
    error = _transient_errors()[0]
    prepare_knowledge_assessment_task.push_request(
        id="task-failure-id", retries=3
    )
    try:
        with (
            patch(
                "sidebrain_back.tasks.knowledge_assessment_task._execute_v2",
                side_effect=error,
            ),
            patch(
                "sidebrain_back.tasks.knowledge_assessment_task."
                "_mark_v2_failed"
            ) as mark_failed,
            pytest.raises(APIConnectionError),
        ):
            prepare_knowledge_assessment_task.run(
                contract_version=2,
                assessment_id=assessment_id,
                user_id=SECRET_USER_ID,
                subject="secret-subject",
            )
    finally:
        prepare_knowledge_assessment_task.pop_request()

    mark_failed.assert_called_once_with(
        assessment_id=assessment_id,
        user_id=SECRET_USER_ID,
        error_code="generation_failed",
    )


def test_v2_invalid_generation_is_definitive_and_sanitized():
    assessment_id = "ae41d14d-8d7e-4b28-9b88-9d74637f54a7"
    with (
        patch(
            "sidebrain_back.tasks.knowledge_assessment_task._execute_v2",
            side_effect=ValueError("secret raw provider payload"),
        ),
        patch(
            "sidebrain_back.tasks.knowledge_assessment_task._mark_v2_failed"
        ) as mark_failed,
        patch.object(prepare_knowledge_assessment_task, "retry") as retry,
        pytest.raises(ValueError),
    ):
        prepare_knowledge_assessment_task.run(
            contract_version=2,
            assessment_id=assessment_id,
            user_id=SECRET_USER_ID,
            subject="secret-subject",
        )

    retry.assert_not_called()
    mark_failed.assert_called_once_with(
        assessment_id=assessment_id,
        user_id=SECRET_USER_ID,
        error_code="invalid_generation_result",
    )


@pytest.mark.anyio
async def test_v2_skip_never_constructs_provider_and_is_idempotent():
    user_id = uuid4()
    assessment_id = uuid4()
    try:
        async with async_session() as seed_db:
            seed_db.add(
                User(
                    usr_id=user_id,
                    usr_email=f"{uuid4()}@example.com",
                    usr_name="Skip User",
                    usr_password_hash="test-hash",
                    usr_is_deleted=False,
                )
            )
            repository = KnowledgeAssessmentRepository(seed_db)
            await repository.create_pending(
                assessment_id=assessment_id,
                user_id=user_id,
                subject="Álgebra",
                objective=None,
                skip=True,
                context_fingerprint=uuid4().hex * 2,
            )
            await seed_db.commit()

        with patch(
            "sidebrain_back.tasks.knowledge_assessment_task."
            "KnowledgeAssessmentGenerator",
            side_effect=AssertionError("provider must not be constructed"),
        ):
            first = await _process_v2(
                assessment_id=str(assessment_id),
                user_id=str(user_id),
                subject="Álgebra",
                objective=None,
                skip=True,
            )
            second = await _process_v2(
                assessment_id=str(assessment_id),
                user_id=str(user_id),
                subject="Álgebra",
                objective=None,
                skip=True,
            )

        assert first == {
            "assessment_id": str(assessment_id),
            "status": "skipped",
        }
        assert second == first
        async with async_session() as verify_db:
            persisted = await KnowledgeAssessmentRepository(
                verify_db
            ).get_accessible(assessment_id, user_id)
            assert persisted is not None
            assert (
                persisted.kas_status
                is KnowledgeAssessmentStatusEnum.SKIPPED
            )
            assert persisted.kas_level.value == "beginner"
            assert persisted.kas_score is None
            assert persisted.kas_completed_at is not None
            assert persisted.questions == []
    finally:
        async with async_session() as cleanup_db:
            await cleanup_db.execute(
                delete(User).where(User.usr_id == user_id)
            )
            await cleanup_db.commit()
        await engine.dispose()
