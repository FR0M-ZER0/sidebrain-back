from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.mentor_generation_model import MentorPrivacyBlock
from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
    get_mentor_consent_repository,
)
from sidebrain_back.services.mentor_consent_service import (
    MentorConsentUnavailable,
)


class MentorPrivacyService:
    """Coordinate deletion with durable send reservations."""

    def __init__(
        self, repository: MentorConsentRepository, db: AsyncSession
    ) -> None:
        self.repository = repository
        self.db = db

    async def lock_for_deletion(self, user_id: UUID) -> MentorPrivacyBlock:
        try:
            block = await self.repository.lock_privacy(user_id)
            if block.blocked and block.reason != "deletion":
                raise MentorConsentUnavailable(
                    "Há outra operação de privacidade pendente."
                )
            block.blocked = True
            block.reason = "deletion"
            if await self.repository.has_inflight(user_id):
                await self.db.commit()
                raise MentorConsentUnavailable(
                    "Há um envio em andamento ou inconclusivo."
                )
            # The caller must delete and clear this block in this transaction.
            return block
        except MentorConsentUnavailable:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise


def get_mentor_privacy_service(
    repository: MentorConsentRepository = Depends(  # noqa: B008
        get_mentor_consent_repository
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MentorPrivacyService:
    return MentorPrivacyService(repository, db)
