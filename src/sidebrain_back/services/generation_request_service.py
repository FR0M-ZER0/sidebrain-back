from uuid import UUID, uuid4

from sidebrain_back.schemas.generation_schema import (
    GenerationInput,
    LearningContext,
)
from sidebrain_back.services.ai_memory_service import AIMemoryService


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
            "assessment_id": (
                str(context.assessment_id) if context.assessment_id else None
            ),
        }

    @classmethod
    def fingerprint(cls, context: LearningContext) -> str:
        fingerprint, _ = AIMemoryService.fingerprint(
            content_type="track",
            canonical_context=cls.normalize_context(context),
        )
        return fingerprint

    @classmethod
    def build_input(
        cls, context: LearningContext, user_id: UUID, request_id: UUID | None
    ) -> GenerationInput:
        return GenerationInput(
            **context.model_dump(),
            request_id=request_id or uuid4(),
            user_id=user_id,
        )
