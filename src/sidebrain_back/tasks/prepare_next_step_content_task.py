from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import UUID, uuid4

from celery import Task
from groq import APIConnectionError, APITimeoutError, RateLimitError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from sidebrain_back.core.celery_app import celery_app
from sidebrain_back.core.constants import Env
from sidebrain_back.core.database import async_session
from sidebrain_back.core.groq_client import get_groq_client
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.enums.mission_criteria_enum import MissionCriteriaEnum
from sidebrain_back.enums.mission_difficulty_enum import MissionDifficultyEnum
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.repositories.track_repository import TrackRepository

logger = logging.getLogger(__name__)


class GeneratedQuiz(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)


class GeneratedLesson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    quizzes: list[GeneratedQuiz] = Field(default_factory=list)


class GeneratedMission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    difficulty: MissionDifficultyEnum
    xp_reward: int = Field(ge=0)
    criteria: MissionCriteriaEnum
    criteria_value: int = Field(ge=0)


class GeneratedContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lessons: list[GeneratedLesson] = Field(min_length=1)
    missions: list[GeneratedMission] = Field(default_factory=list)


class StepContentGenerator:
    def __init__(self, client: Any | None = None) -> None:
        self.client = client or get_groq_client()

    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=Env.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Gere conteúdo educacional válido somente em JSON."
                    ),
                },
                {"role": "user", "content": json.dumps(context, default=str)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=30,
        )
        content = getattr(response.choices[0].message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Resposta vazia do provedor.")
        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise ValueError("Resposta do provedor inválida.")
        return payload


def _task_context(task: Task, event: str, error: Exception | None = None):
    context: dict[str, object] = {
        "event": event,
        "task_id": task.request.id,
        "attempt": task.request.retries + 1,
    }
    if error is not None:
        context["exception_type"] = type(error).__name__
    return context


def _build_context(step) -> dict[str, Any]:
    previous_steps = [
        {
            "title": previous_step.stp_title,
            "status": previous_step.stp_status.value,
            "lessons": [
                {
                    "title": lesson.lsn_title,
                    "text": lesson.lsn_text,
                }
                for lesson in sorted(
                    previous_step.lessons,
                    key=lambda item: item.lsn_position,
                )
            ],
        }
        for previous_step in step.track.steps
        if previous_step.stp_id != step.stp_id
        and previous_step.stp_is_deleted is False
        and (
            previous_step.stp_updated_at < step.stp_updated_at
            or (
                previous_step.stp_updated_at == step.stp_updated_at
                and previous_step.stp_id.int < step.stp_id.int
            )
        )
    ]
    return {
        "track": {
            "id": str(step.track.trk_id),
            "title": step.track.trk_title,
            "description": step.track.trk_description,
        },
        "step": {
            "id": str(step.stp_id),
            "title": step.stp_title,
            "level": step.stp_level.value,
        },
        "previous_steps": previous_steps,
        "constraints": [
            "Não criar IDs, timestamps ou flags de exclusão.",
            "Não criar Answer, Feedback, LessonFile ou MissionProgress.",
        ],
    }


async def _prepare_step_content(
    step_id: UUID,
    generator: StepContentGenerator | None = None,
) -> dict[str, Any]:
    async with async_session() as db:
        try:
            repository = TrackRepository(db)
            step = await repository.get_step_for_generation(step_id)
            if step is None:
                return {
                    "status": "skipped",
                    "reason": "step_not_found_or_inactive",
                }
            if await repository.has_active_generated_content(step_id):
                return {
                    "status": "skipped",
                    "reason": "content_already_exists",
                }

            raw_content = (generator or StepContentGenerator()).generate(
                _build_context(step)
            )
            content = GeneratedContent.model_validate(raw_content)

            for position, generated_lesson in enumerate(
                content.lessons, start=1
            ):
                lesson = Lesson(
                    lsn_id=uuid4(),
                    lsn_step_id=step.stp_id,
                    lsn_title=generated_lesson.title,
                    lsn_text=generated_lesson.text,
                    lsn_status=LessonStatusEnum.IDLE,
                    lsn_position=position,
                )
                db.add(lesson)
                await db.flush()
                for generated_quiz in generated_lesson.quizzes:
                    db.add(
                        Quiz(
                            qui_id=uuid4(),
                            qui_lesson_id=lesson.lsn_id,
                            qui_question=generated_quiz.question,
                        )
                    )

            for generated_mission in content.missions:
                db.add(
                    Mission(
                        msn_id=uuid4(),
                        msn_step_id=step.stp_id,
                        msn_title=generated_mission.title,
                        msn_difficulty=generated_mission.difficulty,
                        msn_xp_reward=generated_mission.xp_reward,
                        msn_criteria=generated_mission.criteria,
                        msn_criteria_value=generated_mission.criteria_value,
                    )
                )
            await db.commit()
            return {
                "status": "generated",
                "step_id": str(step_id),
                "lessons": len(content.lessons),
                "missions": len(content.missions),
            }
        except Exception:
            await db.rollback()
            raise


@celery_app.task(
    bind=True,
    name="tasks.prepare_next_step_content",
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    autoretry_for=(),
)
def prepare_next_step_content_task(self: Task, step_id: str) -> dict[str, Any]:
    try:
        result = asyncio.run(_prepare_step_content(UUID(step_id)))
    except (APIConnectionError, APITimeoutError, RateLimitError) as exc:
        if self.request.retries >= self.max_retries:
            logger.error(
                "Incremental step content failed after retries.",
                extra=_task_context(self, "step_content_failed", exc),
            )
            raise
        logger.warning(
            "Incremental step content retry scheduled.",
            extra=_task_context(self, "step_content_retry_scheduled", exc),
        )
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
    except (ValueError, ValidationError, json.JSONDecodeError) as exc:
        logger.error(
            "Incremental step content rejected.",
            extra=_task_context(self, "step_content_invalid", exc),
        )
        raise
    except Exception as exc:
        logger.error(
            "Incremental step content failed.",
            extra=_task_context(self, "step_content_failed", exc),
        )
        raise

    logger.info(
        "Incremental step content finished.",
        extra=_task_context(self, "step_content_finished"),
    )
    return result
