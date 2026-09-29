from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from celery import Task
from groq import APIConnectionError, APITimeoutError, RateLimitError

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.core.database import async_session, engine
from sidebrain_back.repositories.knowledge_assessment_repository import (
    KnowledgeAssessmentRepository,
)
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
TRANSIENT_PROVIDER_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)


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


async def _process_v2(
    *,
    assessment_id: str,
    user_id: str,
    subject: str,
    objective: str | None,
    skip: bool,
) -> dict[str, str]:
    async with async_session() as db:
        repository = KnowledgeAssessmentRepository(db)
        generator = None if skip else KnowledgeAssessmentGenerator()
        service = KnowledgeAssessmentService(
            generator,
            repository=repository,
            db=db,
        )
        status = await service.process_persisted_assessment(
            assessment_id=UUID(assessment_id),
            user_id=UUID(user_id),
            subject=subject,
            objective=objective,
            skip=skip,
        )
        return {
            "assessment_id": assessment_id,
            "status": status.value,
        }


def _execute_v2(
    *,
    assessment_id: str,
    user_id: str,
    subject: str,
    objective: str | None,
    skip: bool,
) -> dict[str, str]:
    async def run_and_dispose() -> dict[str, str]:
        try:
            return await _process_v2(
                assessment_id=assessment_id,
                user_id=user_id,
                subject=subject,
                objective=objective,
                skip=skip,
            )
        finally:
            await engine.dispose()

    return asyncio.run(run_and_dispose())


async def _persist_v2_failure(
    *,
    assessment_id: str,
    user_id: str,
    error_code: str,
) -> None:
    async with async_session() as db:
        service = KnowledgeAssessmentService(
            repository=KnowledgeAssessmentRepository(db),
            db=db,
        )
        await service.fail_preparation(
            assessment_id=UUID(assessment_id),
            user_id=UUID(user_id),
            error_code=error_code,
        )


def _mark_v2_failed(
    *,
    assessment_id: str,
    user_id: str,
    error_code: str,
) -> None:
    async def run_and_dispose() -> None:
        try:
            await _persist_v2_failure(
                assessment_id=assessment_id,
                user_id=user_id,
                error_code=error_code,
            )
        finally:
            await engine.dispose()

    asyncio.run(run_and_dispose())


@celery_app.task(
    bind=True,
    name="tasks.prepare_knowledge_assessment",
    max_retries=3,
    autoretry_for=(),
)
def prepare_knowledge_assessment_task(
    self: Task,
    user_id: str,
    subject: str | None = None,
    objective: str | None = None,
    skip: bool = False,
    *,
    contract_version: int = 1,
    assessment_id: str | None = None,
) -> dict:
    is_v2 = contract_version == 2
    try:
        if is_v2:
            if assessment_id is None or subject is None:
                raise ValueError("Contrato v2 inválido.")
            payload = _execute_v2(
                assessment_id=assessment_id,
                user_id=user_id,
                subject=subject,
                objective=objective,
                skip=bool(skip),
            )
        else:
            service = KnowledgeAssessmentService(
                KnowledgeAssessmentGenerator()
            )
            context = AssessmentContext(
                user_id=user_id,
                subject=subject,
                objective=objective,
                skip=bool(skip),
            )
            result = service.prepare_assessment(context)
            payload = (
                result
                if isinstance(result, dict)
                else result.model_dump(mode="json")
            )
    except TRANSIENT_PROVIDER_ERRORS as error:
        if self.request.retries >= self.max_retries:
            if is_v2 and assessment_id is not None:
                _mark_v2_failed(
                    assessment_id=assessment_id,
                    user_id=user_id,
                    error_code="generation_failed",
                )
            logger.error(
                "Knowledge assessment failed after retries.",
                extra=_log_context(
                    self,
                    "knowledge_assessment_failed",
                    error,
                ),
            )
            raise
        logger.warning(
            "Knowledge assessment retry scheduled.",
            extra=_log_context(
                self,
                "knowledge_assessment_retry_scheduled",
                error,
            ),
        )
        raise self.retry(
            exc=error,
            countdown=2**self.request.retries,
        ) from error
    except Exception as error:
        if is_v2 and assessment_id is not None:
            error_code = (
                "invalid_generation_result"
                if isinstance(error, ValueError)
                else "generation_failed"
            )
            _mark_v2_failed(
                assessment_id=assessment_id,
                user_id=user_id,
                error_code=error_code,
            )
        logger.error(
            "Knowledge assessment failed.",
            extra=_log_context(
                self,
                "knowledge_assessment_failed",
                error,
            ),
        )
        raise

    logger.info(
        "Knowledge assessment succeeded.",
        extra=_log_context(self, "knowledge_assessment_succeeded"),
    )
    return payload
