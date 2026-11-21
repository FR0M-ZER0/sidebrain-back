from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.mentor_conversation_model import MentorConversation
from sidebrain_back.models.mentor_message_model import MentorMessage
from sidebrain_back.models.track_model import Track


class MentorConversationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, user_id: UUID, track_id: UUID
    ) -> MentorConversation | None:
        track = await self.db.scalar(
            select(Track)
            .where(
                Track.trk_id == track_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
            .with_for_update()
        )
        if track is None:
            return None
        conversation = MentorConversation(user_id=user_id, track_id=track_id)
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get(
        self, user_id: UUID, conversation_id: UUID
    ) -> MentorConversation | None:
        return await self.db.scalar(
            select(MentorConversation)
            .join(Track, Track.trk_id == MentorConversation.track_id)
            .where(
                MentorConversation.id == conversation_id,
                MentorConversation.user_id == user_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
        )

    async def list(
        self,
        user_id: UUID,
        offset: int,
        limit: int,
        track_id: UUID | None = None,
    ) -> tuple[list[MentorConversation], int]:
        filters = [
            MentorConversation.user_id == user_id,
            Track.trk_user_id == user_id,
            Track.trk_is_deleted.is_(False),
        ]
        if track_id is not None:
            filters.append(MentorConversation.track_id == track_id)
        base = (
            select(MentorConversation)
            .join(Track, Track.trk_id == MentorConversation.track_id)
            .where(*filters)
        )
        total = await self.db.scalar(
            select(func.count()).select_from(base.subquery())
        )
        result = await self.db.scalars(
            base.order_by(
                MentorConversation.updated_at.desc(),
                MentorConversation.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(result), int(total or 0)

    async def get_message(
        self, user_id: UUID, conversation_id: UUID, message_id: UUID
    ) -> MentorMessage | None:
        if await self.get(user_id, conversation_id) is None:
            return None
        return await self.db.scalar(
            select(MentorMessage).where(
                MentorMessage.id == message_id,
                MentorMessage.conversation_id == conversation_id,
            )
        )

    async def list_messages(
        self,
        user_id: UUID,
        conversation_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[MentorMessage], int] | None:
        if await self.get(user_id, conversation_id) is None:
            return None
        query = select(MentorMessage).where(
            MentorMessage.conversation_id == conversation_id
        )
        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )
        rows = await self.db.scalars(
            query.order_by(MentorMessage.sequence).offset(offset).limit(limit)
        )
        return list(rows), int(total or 0)

    async def delete(
        self, user_id: UUID, conversation_id: UUID | None = None
    ) -> None:
        query = delete(MentorConversation).where(
            MentorConversation.user_id == user_id
        )
        if conversation_id is not None:
            query = query.where(MentorConversation.id == conversation_id)
        await self.db.execute(query)

    async def delete_by_track_id(self, user_id: UUID, track_id: UUID) -> None:
        await self.db.execute(
            delete(MentorConversation).where(
                MentorConversation.user_id == user_id,
                MentorConversation.track_id == track_id,
            )
        )


def get_mentor_conversation_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MentorConversationRepository:
    return MentorConversationRepository(db)
