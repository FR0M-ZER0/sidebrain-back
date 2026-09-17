from __future__ import annotations

from groq import APIConnectionError, APITimeoutError, RateLimitError

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.schemas.knowledge_assessment_schema import AssessmentContext
from sidebrain_back.services.knowledge_assessment_generator import (
    KnowledgeAssessmentGenerator,
)
from sidebrain_back.services.knowledge_assessment_service import (
    KnowledgeAssessmentService,
)


@celery_app.task(
    bind=True,
    name="tasks.prepare_knowledge_assessment",
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    autoretry_for=(),
)
def prepare_knowledge_assessment(
    self,
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
            return result
        return result.model_dump(mode="json")
    except (APIConnectionError, APITimeoutError, RateLimitError) as exc:
        if self.request.retries >= 3:
            raise
        raise self.retry(exc=exc, countdown=2 ** self.request.retries) from exc
