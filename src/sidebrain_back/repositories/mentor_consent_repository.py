from uuid import UUID, uuid4

from fastapi import Depends
from sqlalchemy import exists, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.mentor_consent_model import MentorConsent
from sidebrain_back.models.mentor_generation_model import (
    MentorPrivacyBlock,
    MentorSendReservation,
)

MENTOR_CONSENT_PURPOSE = "mentor_external_ai"


class MentorConsentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: UUID) -> MentorConsent | None:
        return await self.db.scalar(
            select(MentorConsent).where(
                MentorConsent.user_id == user_id,
                MentorConsent.purpose == MENTOR_CONSENT_PURPOSE,
            )
        )

    async def accept(self, user_id: UUID, version: str) -> MentorConsent:
        statement = insert(MentorConsent).values(
            id=uuid4(),
            user_id=user_id,
            purpose=MENTOR_CONSENT_PURPOSE,
            notice_version=version,
            granted_at=func.now(),
            revoked_at=None,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_mentor_consent_user",
            set_={
                "notice_version": version,
                "granted_at": func.now(),
                "revoked_at": None,
            },
        ).returning(MentorConsent)
        return (
            await self.db.scalars(
                statement.execution_options(populate_existing=True)
            )
        ).one()

    async def revoke(self, user_id: UUID) -> None:
        await self.db.execute(
            update(MentorConsent)
            .where(
                MentorConsent.user_id == user_id,
                MentorConsent.purpose == MENTOR_CONSENT_PURPOSE,
                MentorConsent.revoked_at.is_(None),
            )
            .values(revoked_at=func.now())
            .execution_options(synchronize_session="fetch")
        )

    async def lock_privacy(self, user_id: UUID) -> MentorPrivacyBlock:
        await self.db.execute(
            insert(MentorPrivacyBlock)
            .values(user_id=user_id, blocked=False)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        result = await self.db.scalar(
            select(MentorPrivacyBlock)
            .where(MentorPrivacyBlock.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert result is not None
        return result

    async def get_privacy(self, user_id: UUID) -> MentorPrivacyBlock | None:
        return await self.db.get(MentorPrivacyBlock, user_id)

    async def has_inflight(self, user_id: UUID) -> bool:
        return bool(
            await self.db.scalar(
                select(
                    exists().where(
                        MentorSendReservation.user_id == user_id,
                        MentorSendReservation.status == "in_flight",
                    )
                )
            )
        )


def get_mentor_consent_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MentorConsentRepository:
    return MentorConsentRepository(db)
