import logging
from uuid import UUID

from fastapi import Depends

from sidebrain_back.repositories.step_summary_repository import (
    StepSummaryRepository,
    get_step_summary_repository,
)
from sidebrain_back.services.step_summary_classifier_service import (
    StepSummaryClassifierService,
    get_step_summary_classifier_service,
)
from sidebrain_back.services.step_summary_generator_service import (
    StepSummaryGeneratorService,
)

logger = logging.getLogger(__name__)


class StepSummaryService:
    def __init__(
        self,
        repository: StepSummaryRepository,
        generator: StepSummaryGeneratorService | None = None,
    ):
        self.repository = repository
        self.generator = generator or StepSummaryGeneratorService()

    async def refresh_summary_for_quiz(
        self, user_id: UUID, quiz_id: UUID
    ) -> None:
        step_id = await self.repository.get_step_id_by_quiz_id(
            user_id, quiz_id
        )
        if step_id is None:
            return

        await self.generate_summary_for_step(user_id, step_id)

    async def generate_summary_for_step(
        self, user_id: UUID, step_id: UUID
    ) -> str:
        try:
            answers = await self.repository.list_answers_by_step_id(
                user_id, step_id
            )
            answers_with_reasons = [
                (reason.strip(), rate)
                for reason, rate in answers
                if reason and reason.strip()
            ]
            summary = self.generator.generate_step_summary(
                answers_with_reasons
            )
            await self.repository.update_summary(step_id, summary)
            return summary
        except Exception:
            logger.exception(
                "Falha ao gerar sumário da etapa",
                extra={
                    "user_id": str(user_id),
                    "step_id": str(step_id),
                },
            )
            raise


def get_step_summary_service(
    repository: StepSummaryRepository = Depends(  # noqa: B008
        get_step_summary_repository
    ),
    classifier: StepSummaryClassifierService = Depends(  # noqa: B008
        get_step_summary_classifier_service
    ),
) -> StepSummaryService:
    generator = StepSummaryGeneratorService(classifier)
    return StepSummaryService(repository, generator)
