from __future__ import annotations

import logging

from celery import Task
from groq import APIConnectionError, APITimeoutError, RateLimitError

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentContext,
)
from sidebrain_back.services.knowledge_assessment_generator import (
    KnowledgeAssessmentGenerator,
)
from sidebrain_back.services.knowledge_assessment_service import (
    KnowledgeAssessmentService,
)

logger = logging.getLogger(__name__)


def _log_context(
    task: Task,
    event: str,
    error: Exception | None = None,
) -> dict[str, object]:
    context: dict[str, object] = {
        "event": event,
        "task_id": task.request.id,
        "attempt": task.request.retries + 1,
    }
    if error is not None:
        context["exception_type"] = type(error).__name__
    return context


@celery_app.task(
    bind=True,
    name="tasks.prepare_knowledge_assessment",
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    autoretry_for=(),
)
def prepare_knowledge_assessment_task(
    self: Task,
    user_id: str,
    subject: str | None = None,
    objective: str | None = None,
    skip: bool = False,
) -> dict:
    try:
        service = KnowledgeAssessmentService(KnowledgeAssessmentGenerator())
        context = AssessmentContext(
            user_id=user_id,
            subject=subject,
            objective=objective,
            skip=bool(skip),
        )
        result = service.prepare_assessment(context)
        if isinstance(result, dict):
            payload = result
        else:
            payload = result.model_dump(mode="json")
    except (APIConnectionError, APITimeoutError, RateLimitError) as exc:
        if self.request.retries >= self.max_retries:
            logger.error(
                "Knowledge assessment failed after retries.",
                extra=_log_context(
                    self,
                    "knowledge_assessment_failed",
                    exc,
                ),
            )
            raise
        logger.warning(
            "Knowledge assessment retry scheduled.",
            extra=_log_context(
                self,
                "knowledge_assessment_retry_scheduled",
                exc,
            ),
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries) from exc
    except Exception as exc:
        logger.error(
            "Knowledge assessment failed.",
            extra=_log_context(
                self,
                "knowledge_assessment_failed",
                exc,
            ),
        )
        raise

    logger.info(
        "Knowledge assessment succeeded.",
        extra=_log_context(self, "knowledge_assessment_succeeded"),
    )
    return payload
