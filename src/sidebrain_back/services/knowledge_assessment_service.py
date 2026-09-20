from __future__ import annotations

from uuid import uuid4

from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentContext,
    KnowledgeAssessmentResult,
)


class KnowledgeAssessmentService:
    def __init__(self, generator) -> None:
        self.generator = generator

    def prepare_assessment(
        self, context: AssessmentContext
    ) -> KnowledgeAssessmentResult:
        if context.skip:
            return KnowledgeAssessmentResult(
                assessment_id=str(uuid4()),
                status="skipped",
                level="beginner",
                questions=[],
            )

        subject = (context.subject or "").strip()
        if not subject:
            raise ValueError("Assunto obrigatório para geração da avaliação.")

        objective = context.objective.strip() if context.objective else None

        raw_result = self.generator.generate(subject, objective)
        if not isinstance(raw_result, dict):
            raise ValueError("Resultado inválido retornado pelo gerador.")

        result = KnowledgeAssessmentResult.model_validate(raw_result)
        return result
