import asyncio
import logging

from celery.exceptions import MaxRetriesExceededError
from groq import APIConnectionError, APITimeoutError, RateLimitError
from pydantic import ValidationError

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.core.database import async_session
from sidebrain_back.repositories.generation_repository import (
    GenerationRepository,
)
from sidebrain_back.schemas.generation_schema import (
    GenerationFailure,
    GenerationInput,
)
from sidebrain_back.services.generation_errors import GenerationError
from sidebrain_back.services.generation_service import GenerationService

logger = logging.getLogger(__name__)
TRANSIENT_ERRORS = (APIConnectionError, APITimeoutError, RateLimitError)


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
        return GenerationFailure(
            request_id=request_id, error_code="generation_input_invalid"
        ).model_dump(mode="json")
    try:
        return asyncio.run(_run_generation(payload))
    except TRANSIENT_ERRORS as error:
        try:
            raise self.retry(exc=error)
        except MaxRetriesExceededError:
            logger.warning(
                "track generation retries exhausted",
                extra={
                    "request_id": str(payload.request_id),
                    "task_id": self.request.id,
                    "error_category": "transient",
                },
            )
            return GenerationFailure(
                request_id=payload.request_id,
                error_code="generation_transient_failed",
            ).model_dump(mode="json")
    except GenerationError as error:
        logger.warning(
            "track generation failed",
            extra={
                "request_id": str(payload.request_id),
                "task_id": self.request.id,
                "error_category": error.code,
            },
        )
        return GenerationFailure(
            request_id=payload.request_id, error_code=error.code
        ).model_dump(mode="json")


async def _run_generation(payload: GenerationInput) -> dict:
    async with async_session() as db:
        service = GenerationService(GenerationRepository(db), db)
        result = await service.generate(payload)
        return result.model_dump(mode="json")
