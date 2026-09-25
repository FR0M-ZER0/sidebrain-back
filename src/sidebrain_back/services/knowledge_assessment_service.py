from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.knowledge_assessment_repository import (
    KnowledgeAssessmentRepository,
    get_knowledge_assessment_repository,
)
from sidebrain_back.schemas.knowledge_assessment_schema import (
    AssessmentAcceptedResponse,
    AssessmentAnswersRequest,
    AssessmentContext,
    AssessmentCreateRequest,
    AssessmentDetail,
    GeneratedAssessmentPayload,
    KnowledgeAssessmentResult,
    level_for_score,
)

if TYPE_CHECKING:
    from sidebrain_back.services.knowledge_assessment_generator import (
        KnowledgeAssessmentGenerator,
    )


class KnowledgeAssessmentService:
    def __init__(
        self,
        generator: KnowledgeAssessmentGenerator | object | None = None,
        *,
        repository: KnowledgeAssessmentRepository | None = None,
        db: AsyncSession | None = None,
        publisher: object | None = None,
    ) -> None:
        self.generator = generator
        self.repository = repository
        self.db = db
        self.publisher = publisher

    def prepare_assessment(
        self, context: AssessmentContext
    ) -> KnowledgeAssessmentResult:
        """Execute the temporary v1 in-memory contract."""
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
        if self.generator is None:
            raise RuntimeError("Generator não configurado.")

        raw_result = self.generator.generate(subject, objective)
        if isinstance(raw_result, GeneratedAssessmentPayload):
            return KnowledgeAssessmentResult(
                assessment_id=str(uuid4()),
                status="generated",
                level=None,
                questions=[
                    question.model_dump(exclude={"correct_alternative_id"})
                    for question in raw_result.questions
                ],
            )
        if not isinstance(raw_result, dict):
            raise ValueError("Resultado inválido retornado pelo gerador.")

        payload = dict(raw_result)
        try:
            UUID(str(payload.get("assessment_id")))
        except (ValueError, AttributeError, TypeError):
            payload["assessment_id"] = str(uuid4())
        return KnowledgeAssessmentResult.model_validate(payload)

    @staticmethod
    def context_fingerprint(payload: AssessmentCreateRequest) -> str:
        canonical = json.dumps(
            {
                "objective": payload.objective,
                "skip": payload.skip,
                "subject": payload.subject,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async def create_knowledge_assessment(
        self,
        user: User,
        payload: AssessmentCreateRequest,
    ) -> AssessmentAcceptedResponse:
        repository, db = self._persistence()
        fingerprint = self.context_fingerprint(payload)
        existing = await repository.get_active_by_fingerprint(
            user.usr_id, fingerprint
        )
        if existing is not None:
            return self._accepted(existing)

        try:
            assessment = await repository.create_pending(
                assessment_id=uuid4(),
                user_id=user.usr_id,
                subject=payload.subject,
                objective=payload.objective,
                skip=payload.skip,
                context_fingerprint=fingerprint,
            )
            await db.commit()
        except IntegrityError:
            await db.rollback()
            winner = await repository.get_active_by_fingerprint(
                user.usr_id, fingerprint
            )
            if winner is None:
                raise
            return self._accepted(winner)

        try:
            self._task_publisher().apply_async(
                kwargs={
                    "contract_version": 2,
                    "assessment_id": str(assessment.kas_id),
                    "user_id": str(user.usr_id),
                    "subject": payload.subject,
                    "objective": payload.objective,
                    "skip": payload.skip,
                }
            )
        except Exception as error:
            await repository.mark_failed(assessment, "generation_failed")
            await db.commit()
            raise ProblemDetailError(
                503,
                "Serviço indisponível",
                "Não foi possível iniciar a avaliação.",
                error_code="generation_failed",
            ) from error
        return self._accepted(assessment)

    async def get_knowledge_assessment(
        self,
        user: User,
        assessment_id: UUID,
    ) -> AssessmentDetail:
        repository, _db = self._persistence()
        assessment = await repository.get_accessible(
            assessment_id, user.usr_id
        )
        if assessment is None:
            raise self._not_found()
        return AssessmentDetail.model_validate(assessment)

    async def submit_knowledge_assessment_answers(
        self,
        user: User,
        assessment_id: UUID,
        payload: AssessmentAnswersRequest,
    ) -> AssessmentDetail:
        repository, db = self._persistence()
        try:
            assessment = await repository.get_for_update(
                assessment_id, user.usr_id
            )
            if assessment is None:
                raise self._not_found()
            if (
                assessment.kas_status
                is not KnowledgeAssessmentStatusEnum.GENERATED
            ):
                raise ProblemDetailError(
                    409,
                    "Conflito",
                    "A avaliação não está disponível para submissão.",
                    error_code="assessment_not_generated",
                )

            questions = {
                question.kaq_id: question
                for question in assessment.questions
            }
            submitted_question_ids = {
                answer.question_id for answer in payload.answers
            }
            if submitted_question_ids != set(questions):
                raise ProblemDetailError(
                    422,
                    "Erro de validação",
                    "Requisição inválida.",
                    errors=[
                        {
                            "field": "body.answers",
                            "message": (
                                "As respostas devem corresponder às cinco "
                                "perguntas da avaliação."
                            ),
                        }
                    ],
                )

            score = 0
            for index, answer in enumerate(payload.answers):
                question = questions[answer.question_id]
                alternatives = {
                    alternative.kaa_id: alternative
                    for alternative in question.alternatives
                }
                selected = alternatives.get(answer.alternative_id)
                if selected is None:
                    raise ProblemDetailError(
                        422,
                        "Erro de validação",
                        "Requisição inválida.",
                        errors=[
                            {
                                "field": (
                                    f"body.answers.{index}.alternative_id"
                                ),
                                "message": (
                                    "Alternativa inválida para a pergunta "
                                    "informada."
                                ),
                            }
                        ],
                    )
                score += int(selected.kaa_is_correct)

            await repository.complete(
                assessment,
                payload.answers,
                score=score,
                level=level_for_score(score),
            )
            await db.commit()
            return AssessmentDetail.model_validate(assessment)
        except ProblemDetailError:
            await db.rollback()
            raise
        except Exception as error:
            await db.rollback()
            raise ProblemDetailError(
                500,
                "Erro interno",
                "Não foi possível processar a operação.",
            ) from error

    async def process_persisted_assessment(
        self,
        *,
        assessment_id: UUID,
        user_id: UUID,
        subject: str,
        objective: str | None,
        skip: bool,
    ) -> KnowledgeAssessmentStatusEnum:
        repository, db = self._persistence()
        assessment = await repository.get_accessible(assessment_id, user_id)
        if assessment is None:
            raise ValueError("Avaliação pendente não encontrada.")
        if assessment.kas_status is not KnowledgeAssessmentStatusEnum.PENDING:
            return assessment.kas_status
        if (
            assessment.kas_subject != subject
            or assessment.kas_objective != objective
            or assessment.kas_skip is not skip
        ):
            raise ValueError("Contexto da avaliação divergente.")

        if skip:
            locked = await repository.get_for_update(assessment_id, user_id)
            if locked is None:
                raise ValueError("Avaliação pendente não encontrada.")
            await repository.mark_skipped(locked)
            await db.commit()
            return locked.kas_status

        if self.generator is None:
            raise RuntimeError("Generator não configurado.")
        generated = self.generator.generate(subject, objective)
        payload = GeneratedAssessmentPayload.model_validate(generated)
        locked = await repository.get_for_update(assessment_id, user_id)
        if locked is None:
            raise ValueError("Avaliação pendente não encontrada.")
        await repository.mark_generated(locked, payload)
        await db.commit()
        return locked.kas_status

    async def fail_preparation(
        self,
        *,
        assessment_id: UUID,
        user_id: UUID,
        error_code: str,
    ) -> KnowledgeAssessmentStatusEnum | None:
        repository, db = self._persistence()
        assessment = await repository.get_for_update(assessment_id, user_id)
        if assessment is None:
            return None
        await repository.mark_failed(assessment, error_code)
        await db.commit()
        return assessment.kas_status

    def _persistence(
        self,
    ) -> tuple[KnowledgeAssessmentRepository, AsyncSession]:
        if self.repository is None or self.db is None:
            raise RuntimeError("Persistência da avaliação não configurada.")
        return self.repository, self.db

    def _task_publisher(self):
        if self.publisher is not None:
            return self.publisher
        from sidebrain_back.tasks.knowledge_assessment_task import (
            prepare_knowledge_assessment_task,
        )

        return prepare_knowledge_assessment_task

    @staticmethod
    def _accepted(assessment) -> AssessmentAcceptedResponse:
        return AssessmentAcceptedResponse(
            assessment_id=assessment.kas_id,
            status=assessment.kas_status,
        )

    @staticmethod
    def _not_found() -> ProblemDetailError:
        return ProblemDetailError(
            404,
            "Não encontrado",
            "Avaliação não encontrada.",
        )


def get_knowledge_assessment_service(
    repository: KnowledgeAssessmentRepository = Depends(  # noqa: B008
        get_knowledge_assessment_repository
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> KnowledgeAssessmentService:
    return KnowledgeAssessmentService(repository=repository, db=db)
