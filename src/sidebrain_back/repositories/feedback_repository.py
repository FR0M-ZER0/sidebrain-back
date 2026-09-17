from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.models.feedback_model import Feedback
from sidebrain_back.models.lesson_model import Lesson


class FeedbackRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def lesson_exists(self, lesson_id: UUID) -> bool:
        result = await self.db.scalar(
            select(Lesson.lsn_id).where(
                Lesson.lsn_id == lesson_id,
                Lesson.lsn_is_deleted.is_(False),
            )
        )
        return result is not None

    async def create(
        self, lesson_id: UUID, user_id: UUID, text: str
    ) -> Feedback:
        feedback = Feedback(
            fbk_lesson_id=lesson_id,
            fbk_user_id=user_id,
            fbk_text=text,
            fbk_is_deleted=False,
            fbk_deleted_at=None,
        )
        self.db.add(feedback)
        await self.db.flush()
        return feedback

    async def list_by_lesson_id(
        self, lesson_id: UUID, offset: int, limit: int
    ) -> tuple[list[Feedback], int]:
        filters = (
            Feedback.fbk_lesson_id == lesson_id,
            Feedback.fbk_is_deleted.is_(False),
        )
        total = await self.db.scalar(
            select(func.count()).select_from(Feedback).where(*filters)
        )
        result = await self.db.execute(
            select(Feedback)
            .where(*filters)
            .order_by(Feedback.fbk_created_at.desc(), Feedback.fbk_id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(total or 0)

    async def get(self, feedback_id: UUID) -> Feedback | None:
        result = await self.db.execute(
            select(Feedback)
            .join(Lesson, Lesson.lsn_id == Feedback.fbk_lesson_id)
            .where(
                Feedback.fbk_id == feedback_id,
                Feedback.fbk_is_deleted.is_(False),
                Lesson.lsn_is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def update(self, feedback: Feedback, text: str) -> Feedback:
        feedback.fbk_text = text
        feedback.fbk_updated_at = datetime.now(UTC).replace(tzinfo=None)
        return feedback

    async def soft_delete(self, feedback: Feedback) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        feedback.fbk_is_deleted = True
        feedback.fbk_deleted_at = now
        feedback.fbk_updated_at = now


def get_feedback_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> FeedbackRepository:
    return FeedbackRepository(db)
