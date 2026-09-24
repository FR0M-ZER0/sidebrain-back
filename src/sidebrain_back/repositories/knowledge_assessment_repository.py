from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.models.knowledge_assessment_alternative_model import (
    KnowledgeAssessmentAlternative,
)
from sidebrain_back.models.knowledge_assessment_answer_model import (
    KnowledgeAssessmentAnswer,
)
from sidebrain_back.models.knowledge_assessment_model import (
    KnowledgeAssessment,
)
from sidebrain_back.models.knowledge_assessment_question_model import (
    KnowledgeAssessmentQuestion,
)
from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentAnswerInput,
    GeneratedAssessmentPayload,
)


class KnowledgeAssessmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_pending(
        self,
        *,
        assessment_id: UUID,
        user_id: UUID,
        subject: str,
        objective: str | None,
        skip: bool,
        context_fingerprint: str,
    ) -> KnowledgeAssessment:
        assessment = KnowledgeAssessment(
            kas_id=assessment_id,
            kas_user_id=user_id,
            kas_subject=subject,
            kas_objective=objective,
            kas_skip=skip,
            kas_context_fingerprint=context_fingerprint,
            kas_status=KnowledgeAssessmentStatusEnum.PENDING,
            questions=[],
            answers=[],
        )
        self.db.add(assessment)
        await self.db.flush()
        return assessment

    async def get(self, assessment_id: UUID) -> KnowledgeAssessment | None:
        return await self.db.scalar(
            select(KnowledgeAssessment).where(
                KnowledgeAssessment.kas_id == assessment_id
            )
        )

    async def get_active_by_fingerprint(
        self,
        user_id: UUID,
        context_fingerprint: str,
    ) -> KnowledgeAssessment | None:
        return await self.db.scalar(
            select(KnowledgeAssessment).where(
                KnowledgeAssessment.kas_user_id == user_id,
                KnowledgeAssessment.kas_context_fingerprint
                == context_fingerprint,
                KnowledgeAssessment.kas_status.in_(
                    (
                        KnowledgeAssessmentStatusEnum.PENDING,
                        KnowledgeAssessmentStatusEnum.GENERATED,
                    )
                ),
            )
        )

    async def get_accessible(
        self,
        assessment_id: UUID,
        user_id: UUID,
    ) -> KnowledgeAssessment | None:
        result = await self.db.execute(
            self._owned_query(assessment_id, user_id).options(
                *self._hierarchy_options()
            )
        )
        return result.scalars().unique().one_or_none()

    async def get_for_update(
        self,
        assessment_id: UUID,
        user_id: UUID,
    ) -> KnowledgeAssessment | None:
        result = await self.db.execute(
            self._owned_query(assessment_id, user_id)
            .options(*self._hierarchy_options())
            .with_for_update()
        )
        return result.scalars().unique().one_or_none()

    async def mark_generated(
        self,
        assessment: KnowledgeAssessment,
        payload: GeneratedAssessmentPayload,
    ) -> bool:
        if assessment.kas_status is not KnowledgeAssessmentStatusEnum.PENDING:
            return False

        questions: list[KnowledgeAssessmentQuestion] = []
        for question_position, provider_question in enumerate(
            payload.questions,
            start=1,
        ):
            question = KnowledgeAssessmentQuestion(
                kaq_id=uuid4(),
                kaq_assessment_id=assessment.kas_id,
                kaq_statement=provider_question.statement,
                kaq_position=question_position,
            )
            question.alternatives = [
                KnowledgeAssessmentAlternative(
                    kaa_id=uuid4(),
                    kaa_text=alternative.text,
                    kaa_position=alternative_position,
                    kaa_is_correct=(
                        alternative.id
                        == provider_question.correct_alternative_id
                    ),
                )
                for alternative_position, alternative in enumerate(
                    provider_question.alternatives,
                    start=1,
                )
            ]
            questions.append(question)

        assessment.questions = questions
        assessment.kas_status = KnowledgeAssessmentStatusEnum.GENERATED
        assessment.kas_error_code = None
        assessment.kas_updated_at = self._now()
        await self.db.flush()
        return True

    async def mark_failed(
        self,
        assessment: KnowledgeAssessment,
        error_code: str,
    ) -> bool:
        if assessment.kas_status is not KnowledgeAssessmentStatusEnum.PENDING:
            return False
        assessment.kas_status = KnowledgeAssessmentStatusEnum.FAILED
        assessment.kas_error_code = error_code
        assessment.kas_updated_at = self._now()
        await self.db.flush()
        return True

    async def mark_skipped(
        self,
        assessment: KnowledgeAssessment,
    ) -> bool:
        if assessment.kas_status is not KnowledgeAssessmentStatusEnum.PENDING:
            return False
        now = self._now()
        assessment.kas_status = KnowledgeAssessmentStatusEnum.SKIPPED
        assessment.kas_score = None
        assessment.kas_level = StepLevelEnum.BEGINNER
        assessment.kas_error_code = None
        assessment.kas_completed_at = now
        assessment.kas_updated_at = now
        await self.db.flush()
        return True

    async def complete(
        self,
        assessment: KnowledgeAssessment,
        answers: list[AssessmentAnswerInput],
        *,
        score: int,
        level: StepLevelEnum,
    ) -> bool:
        if (
            assessment.kas_status
            is not KnowledgeAssessmentStatusEnum.GENERATED
        ):
            return False
        assessment.answers = [
            KnowledgeAssessmentAnswer(
                kar_id=uuid4(),
                kar_assessment_id=assessment.kas_id,
                kar_question_id=answer.question_id,
                kar_alternative_id=answer.alternative_id,
            )
            for answer in answers
        ]
        now = self._now()
        assessment.kas_status = KnowledgeAssessmentStatusEnum.COMPLETED
        assessment.kas_score = score
        assessment.kas_level = level
        assessment.kas_error_code = None
        assessment.kas_completed_at = now
        assessment.kas_updated_at = now
        await self.db.flush()
        return True

    @staticmethod
    def _owned_query(assessment_id: UUID, user_id: UUID):
        return select(KnowledgeAssessment).where(
            KnowledgeAssessment.kas_id == assessment_id,
            KnowledgeAssessment.kas_user_id == user_id,
        )

    @staticmethod
    def _hierarchy_options():
        return (
            selectinload(KnowledgeAssessment.questions).selectinload(
                KnowledgeAssessmentQuestion.alternatives
            ),
            selectinload(KnowledgeAssessment.answers),
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)


def get_knowledge_assessment_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> KnowledgeAssessmentRepository:
    return KnowledgeAssessmentRepository(db)
