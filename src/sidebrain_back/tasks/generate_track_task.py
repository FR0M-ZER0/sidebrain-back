import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar
from uuid import UUID

from celery.exceptions import MaxRetriesExceededError
from openai import (
    APIConnectionError,
    APITimeoutError,
    OpenAIError,
    RateLimitError,
)
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.core.database import async_session, engine
from sidebrain_back.repositories.badge_progress_repository import (
    BadgeProgressRepository,
)
from sidebrain_back.repositories.generation_repository import (
    GenerationRepository,
)
from sidebrain_back.repositories.generation_request_repository import (
    GenerationRequestRepository,
)
from sidebrain_back.schemas.generation_schema import (
    GenerationFailure,
    GenerationInput,
)
from sidebrain_back.services.badge_progress_service import BadgeProgressService
from sidebrain_back.services.generation_errors import (
    GenerationError,
    GenerationValidationError,
)
from sidebrain_back.services.generation_service import GenerationService
from sidebrain_back.services.rag_generation_context_service import (
    RagGenerationContextService,
    build_rag_generation_context_service,
)

logger = logging.getLogger(__name__)
TRANSIENT_ERRORS = (APIConnectionError, APITimeoutError, RateLimitError)
ResultT = TypeVar("ResultT")


async def _run_and_dispose(
    coroutine: Coroutine[Any, Any, ResultT],
) -> ResultT:
    try:
        return await coroutine
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name="tasks.generate_track",
    max_retries=2,
    autoretry_for=TRANSIENT_ERRORS,
    retry_backoff=True,
    retry_jitter=True,
)
def generate_track_task(self, **kwargs) -> dict:
    try:
        payload = GenerationInput.model_validate(kwargs)
    except ValidationError:
        request_id = kwargs.get("request_id")
        if request_id is None:
            raise
        result = GenerationFailure(
            request_id=request_id, error_code="generation_input_invalid"
        )
        asyncio.run(
            _run_and_dispose(_mark_failed(request_id, result.error_code))
        )
        return result.model_dump(mode="json")
    return asyncio.run(_run_and_dispose(_process_generation(payload, self)))


async def _process_generation(payload: GenerationInput, task) -> dict:
    try:
        return await _run_generation(payload)
    except TRANSIENT_ERRORS as error:
        try:
            task.retry(exc=error)
        except MaxRetriesExceededError:
            logger.warning(
                "track generation retries exhausted",
                extra={
                    "request_id": str(payload.request_id),
                    "task_id": task.request.id,
                    "error_category": "transient",
                },
            )
            result = GenerationFailure(
                request_id=payload.request_id,
                error_code="generation_transient_failed",
            )
            await _mark_failed(payload.request_id, result.error_code)
            return result.model_dump(mode="json")
    except GenerationError as error:
        log_context: dict[str, object] = {
            "request_id": str(payload.request_id),
            "task_id": task.request.id,
            "error_category": error.code,
        }
        message = "track generation failed"
        if isinstance(error, GenerationValidationError):
            log_context["validation_issues"] = error.validation_issues
            if error.validation_issues:
                message += ": " + "; ".join(error.validation_issues)
        logger.warning(
            message,
            extra=log_context,
        )
        result = GenerationFailure(
            request_id=payload.request_id, error_code=error.code
        )
        await _mark_failed(payload.request_id, result.error_code)
        return result.model_dump(mode="json")
    except OpenAIError as error:
        logger.exception(
            "track generation provider request failed",
            extra={
                "request_id": str(payload.request_id),
                "task_id": task.request.id,
                "error_category": type(error).__name__,
            },
        )
        result = GenerationFailure(
            request_id=payload.request_id,
            error_code="generation_provider_failed",
        )
        await _mark_failed(payload.request_id, result.error_code)
        return result.model_dump(mode="json")


async def _run_generation(
    payload: GenerationInput,
    rag_context_service: RagGenerationContextService | None = None,
) -> dict:
    async with async_session() as db:
        repository = GenerationRepository(db)
        service = GenerationService(
            repository,
            db,
            GenerationRequestRepository(db),
            BadgeProgressService(BadgeProgressRepository(db), db),
        )
        references = []
        existing = await repository.get_by_request_id(payload.request_id)
        if existing is None and db.in_transaction():
            await db.rollback()
        context_service = rag_context_service
        owns_context_service = False
        if existing is None and context_service is None:
            context_service = build_rag_generation_context_service()
            owns_context_service = context_service is not None
        if existing is None and context_service is not None:
            try:
                references = await context_service.get_references(
                    goal=payload.goal,
                    topic=payload.topic,
                    level=(
                        payload.knowledge_level.value
                        if payload.knowledge_level
                        else None
                    ),
                )
            except Exception as error:
                logger.warning(
                    "RAG context unavailable for initial generation",
                    extra={
                        "request_id": str(payload.request_id),
                        "error_category": type(error).__name__,
                    },
                )
            finally:
                if owns_context_service:
                    try:
                        await context_service.aclose()
                    except Exception as error:
                        logger.warning(
                            "RAG context service cleanup failed",
                            extra={
                                "error_category": type(error).__name__,
                            },
                        )
        result = await service.generate(
            payload,
            reference_context=references or None,
        )
        return result.model_dump(mode="json")


async def _mark_failed(request_id: str | UUID, error_code: str) -> None:
    try:
        async with async_session() as db:
            await GenerationRequestRepository(db).mark_failed(
                UUID(str(request_id)), error_code
            )
            await db.commit()
    except SQLAlchemyError:
        logger.exception("could not persist generation failure")
