from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.models.mentor_conversation_model import MentorConversation
from sidebrain_back.models.mentor_generation_model import MentorGeneration
from sidebrain_back.repositories.mentor_consent_repository import (
    MentorConsentRepository,
)
from sidebrain_back.repositories.mentor_generation_repository import (
    MentorGenerationRepository,
)
from sidebrain_back.services.mentor_consent_service import MentorConsentService


class MentorDispatchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def collect_pending(self) -> list[tuple[str, str]]:
        repository = MentorGenerationRepository(self.db)
        version, _ = MentorConsentService(
            MentorConsentRepository(self.db), self.db
        )._notice()
        now = datetime.now(UTC).replace(tzinfo=None)
        expired = (
            await self.db.execute(
                select(
                    MentorConversation.user_id,
                    MentorGeneration.id,
                    MentorGeneration.attempt_id,
                )
                .join(
                    MentorConversation,
                    MentorConversation.id == MentorGeneration.conversation_id,
                )
                .where(
                    MentorGeneration.status == "processing",
                    MentorGeneration.attempt_deadline < now,
                    MentorGeneration.attempt_id.is_not(None),
                )
                .limit(100)
            )
        ).all()
        await self.db.rollback()
        for user_id, generation_id, attempt_id in expired:
            await repository.reconcile_expired(
                user_id, generation_id, attempt_id, version
            )
            await self.db.commit()
        queued = (
            await self.db.execute(
                select(MentorConversation.user_id, MentorGeneration.id)
                .join(
                    MentorConversation,
                    MentorConversation.id == MentorGeneration.conversation_id,
                )
                .where(MentorGeneration.status == "queued")
                .order_by(MentorGeneration.created_at, MentorGeneration.id)
                .limit(100)
            )
        ).all()
        return [(str(user_id), str(gen_id)) for user_id, gen_id in queued]
