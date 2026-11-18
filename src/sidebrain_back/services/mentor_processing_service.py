import logging
from uuid import UUID

from openai import APIConnectionError, APITimeoutError, RateLimitError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from sidebrain_back.core.mentor_lock import mentor_user_lock
from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
)
from sidebrain_back.repositories.mentor_context_repository import (
    MentorContextRepository,
)
from sidebrain_back.repositories.mentor_generation_repository import (
    MentorGenerationConflict,
    MentorGenerationConsentRequired,
    MentorGenerationRepository,
)
from sidebrain_back.services.mentor_consent_service import MentorConsentService
from sidebrain_back.services.mentor_context_service import MentorContextService
from sidebrain_back.services.mentor_generator_service import (
    MentorGeneratorService,
)

TRANSIENT_PROVIDER_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    TimeoutError,
)
logger = logging.getLogger(__name__)


class MentorProcessingService:
    def __init__(
        self, db: AsyncSession, generator: MentorGeneratorService
    ) -> None:
        self.db = db
        self.generations = MentorGenerationRepository(db)
        self.consent = MentorConsentService(MentorConsentRepository(db), db)
        self.generator = generator

    async def process(self, user_id: UUID, generation_id: UUID) -> None:
        async with mentor_user_lock(user_id) as connection:
            version, _ = self.consent._notice()
            try:
                reservation = await self.generations.reserve(
                    user_id, generation_id, version
                )
                attempt_id = reservation.attempt_id
                context = await MentorContextService(
                    self.generations, MentorContextRepository(self.db)
                ).build(user_id, generation_id)
                await self.db.commit()
            except MentorGenerationConsentRequired:
                await self.db.rollback()
                await self.generations.fail_unauthorized(
                    user_id, generation_id, version
                )
                await self.db.commit()
                logger.info(
                    "Geração de mentoria sem autorização.",
                    extra={"generation_id": str(generation_id)},
                )
                return
            except MentorGenerationConflict:
                await self.db.rollback()
                return
            except Exception:
                await self.db.rollback()
                raise

            try:
                await self._check_lock_connection(connection)
                result = self.generator.generate(context)
                await self._check_lock_connection(connection)
            except Exception as error:
                # A lost connection cannot establish that the sender stopped.
                await self._check_lock_connection(connection)
                await self.generations.fail_attempt(
                    user_id,
                    generation_id,
                    attempt_id,
                    transient=isinstance(error, TRANSIENT_PROVIDER_ERRORS),
                    notice_version=version,
                )
                await self.db.commit()
                logger.warning(
                    "Falha na geração de mentoria.",
                    extra={
                        "generation_id": str(generation_id),
                        "error_type": type(error).__name__,
                    },
                )
                return
            await self.generations.complete(
                user_id, generation_id, attempt_id, result, version
            )
            await self.db.commit()
            logger.info(
                "Geração de mentoria processada.",
                extra={"generation_id": str(generation_id)},
            )

    @staticmethod
    async def _check_lock_connection(connection: AsyncConnection) -> None:
        if connection.invalidated:
            raise RuntimeError("Bloqueio de mentoria perdido.")
        await connection.execute(text("SELECT 1"))
