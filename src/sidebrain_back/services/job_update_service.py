from uuid import UUID

from fastapi import Depends

from sidebrain_back.core.database import async_session
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.core.ws_tickets import WsTicketStore, get_ws_ticket_store
from sidebrain_back.enums.knowledge_assessment_status_enum import (
    KnowledgeAssessmentStatusEnum,
)
from sidebrain_back.models.user_model import User
from sidebrain_back.repositories.job_update_repository import (
    JobUpdateRepository,
    get_job_update_repository,
)
from sidebrain_back.schemas.job_update_schema import (
    AssessmentAlternativePayload,
    AssessmentPayload,
    AssessmentQuestionPayload,
    JobScope,
    JobUpdated,
    StepPreparationPayload,
    StepSummaryPayload,
    TrackGenerationPayload,
)

RESOURCE_UNAVAILABLE = "Recurso indisponível."


class JobUpdateService:
    def __init__(
        self,
        repository: JobUpdateRepository,
        ticket_store: WsTicketStore,
    ) -> None:
        self.repository = repository
        self.ticket_store = ticket_store

    async def issue_ticket(self, user: User, scope: JobScope) -> str:
        await self.get_snapshot(user.usr_id, scope)
        return await self.ticket_store.issue(
            {
                "user_id": str(user.usr_id),
                "channel": scope.channel,
                "resource_id": scope.resource_id,
            }
        )

    async def get_snapshot(
        self, user_id: UUID, scope: JobScope
    ) -> JobUpdated:
        if not await self.repository.active_user(user_id):
            self._unavailable()
        if scope.channel == "track_generation":
            request = await self.repository.track_generation(
                UUID(scope.resource_id), user_id
            )
            if request is None:
                self._unavailable()
            payload = TrackGenerationPayload(
                request_id=request.request_id,
                status=request.status.value,
                track_id=request.track_id,
                error_code=request.error_code,
            )
        elif scope.channel == "assessment":
            assessment = await self.repository.assessment(
                UUID(scope.resource_id), user_id
            )
            if assessment is None:
                self._unavailable()
            status = assessment.kas_status
            public_status = (
                "pending"
                if status is KnowledgeAssessmentStatusEnum.PENDING
                else "failed"
                if status is KnowledgeAssessmentStatusEnum.FAILED
                else "completed"
            )
            questions = []
            if status in {
                KnowledgeAssessmentStatusEnum.GENERATED,
                KnowledgeAssessmentStatusEnum.COMPLETED,
            }:
                questions = [
                    AssessmentQuestionPayload(
                        id=question.kaq_id,
                        statement=question.kaq_statement,
                        alternatives=[
                            AssessmentAlternativePayload(
                                id=alternative.kaa_id,
                                text=alternative.kaa_text,
                            )
                            for alternative in question.alternatives
                        ],
                    )
                    for question in assessment.questions
                ]
            payload = AssessmentPayload(
                assessment_id=assessment.kas_id,
                status=public_status,
                questions=questions,
                error_code=assessment.kas_error_code,
            )
        elif scope.channel == "step_preparation":
            preparation = await self.repository.step_preparation(
                scope.resource_id, user_id
            )
            if preparation is None:
                self._unavailable()
            payload = StepPreparationPayload(
                task_id=preparation.task_id, status=preparation.status
            )
        else:
            track_text, step_text = scope.resource_id.split(":")
            result = await self.repository.step_summary(
                UUID(track_text), UUID(step_text), user_id
            )
            if result is None:
                self._unavailable()
            step, generation = result
            status = (
                generation.status
                if generation is not None
                else "completed"
            )
            payload = StepSummaryPayload(
                step_id=step.stp_id,
                status=status,
                summary=step.stp_summary if status == "completed" else None,
                error=(
                    "Não foi possível gerar o resumo da etapa."
                    if status == "failed"
                    else None
                ),
            )
        return JobUpdated(
            channel=scope.channel,
            resource_id=scope.resource_id,
            payload=payload,
        )

    @staticmethod
    def _unavailable() -> None:
        raise ProblemDetailError(404, "Não encontrado", RESOURCE_UNAVAILABLE)


def get_job_update_service(
    repository: JobUpdateRepository = Depends(  # noqa: B008
        get_job_update_repository
    ),
    ticket_store: WsTicketStore = Depends(get_ws_ticket_store),  # noqa: B008
) -> JobUpdateService:
    return JobUpdateService(repository, ticket_store)


async def load_job_snapshot(user_id: UUID, scope: JobScope) -> JobUpdated:
    async with async_session() as db:
        return await JobUpdateService(
            JobUpdateRepository(db), get_ws_ticket_store()
        ).get_snapshot(user_id, scope)
