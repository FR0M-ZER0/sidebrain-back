import logging
from uuid import UUID

from fastapi import Depends
from sqlalchemy.exc import IntegrityError

from sidebrain_back.core.database import async_session
from sidebrain_back.repositories.step_summary_generation_repository import (
    StepSummaryGenerationRepository,
)
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
        generation_repository: StepSummaryGenerationRepository | None = None,
    ):
        self.repository = repository
        self.generator = generator or StepSummaryGeneratorService()
        repository_db = getattr(repository, "db", None)
        self.generation_repository = generation_repository
        if self.generation_repository is None and repository_db is not None:
            self.generation_repository = StepSummaryGenerationRepository(
                repository_db
            )
        self._last_generation: tuple[UUID, int] | None = None
        self._last_generation_independent = False

    async def _reserve_generation(self, step_id: UUID) -> int | None:
        if self.generation_repository is None:
            return None
        try:
            async with async_session() as db:
                generation = await StepSummaryGenerationRepository(db).reserve(
                    step_id
                )
                await db.commit()
            self._last_generation_independent = True
        except IntegrityError:
            # Fixtures e criações ainda não confirmadas podem manter o Step
            # invisível para outra conexão. Nessa situação, a FK garante que
            # a reserva permaneça na transação que cria/usa a entidade.
            generation = await self.generation_repository.reserve(step_id)
            self._last_generation_independent = False
        self._last_generation = (step_id, generation)
        return generation

    async def fail_last_generation(self) -> None:
        if (
            self._last_generation is None
            or not self._last_generation_independent
        ):
            return
        step_id, generation = self._last_generation
        async with async_session() as db:
            changed = await StepSummaryGenerationRepository(db).finish(
                step_id, generation, "failed"
            )
            if changed:
                await db.commit()

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
        generation_repository = self.generation_repository
        generation = await self._reserve_generation(step_id)
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
            is_current = generation_repository is None
            if generation_repository is not None and generation is not None:
                is_current = await generation_repository.finish(
                    step_id, generation, "completed"
                )
            if is_current:
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
