import hashlib
import json
from uuid import UUID, uuid4

from sidebrain_back.schemas.generation_schema import (
    GenerationInput,
    LearningContext,
)


class GenerationRequestService:
    @staticmethod
    def normalize_context(context: LearningContext) -> dict:
        return {
            "goal": context.goal.strip(),
            "topic": context.topic.strip(),
            "knowledge_level": (
                context.knowledge_level.value
                if context.knowledge_level
                else None
            ),
            "assessment_answers": [
                answer.model_dump(mode="json")
                for answer in context.assessment_answers or []
            ],
        }

    @classmethod
    def fingerprint(cls, context: LearningContext) -> str:
        normalized = json.dumps(
            cls.normalize_context(context),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def build_input(
        cls, context: LearningContext, user_id: UUID, request_id: UUID | None
    ) -> GenerationInput:
        return GenerationInput(
            **context.model_dump(),
            request_id=request_id or uuid4(),
            user_id=user_id,
        )
