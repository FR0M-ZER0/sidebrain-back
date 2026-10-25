from uuid import UUID

from fastapi import Depends

from sidebrain_back.repositories.step_summary_repository import (
    StepSummaryRepository,
    get_step_summary_repository,
)
from sidebrain_back.services.step_summary_generator_service import (
    StepSummaryGeneratorService,
)


class StepSummaryService:
    def __init__(self, repository: StepSummaryRepository):
        self.repository = repository
        self.generator = StepSummaryGeneratorService()

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
        reasons = await self.repository.list_reasons_by_step_id(
            user_id, step_id
        )
        texts = [
            reason.strip() for reason in reasons if reason and reason.strip()
        ]
        summary = self.generator.generate_step_summary(texts)
        await self.repository.update_summary(step_id, summary)
        return summary


def get_step_summary_service(
    repository: StepSummaryRepository = Depends(  # noqa: B008
        get_step_summary_repository
    ),
) -> StepSummaryService:
    return StepSummaryService(repository)
