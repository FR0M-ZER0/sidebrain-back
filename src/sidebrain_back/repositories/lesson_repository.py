from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.models.feedback_model import Feedback
from sidebrain_back.models.lesson_file_model import LessonFile
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track


class LessonRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_accessible_step(
        self,
        user_id: UUID,
        step_id: UUID,
    ) -> Step | None:
        return await self.db.scalar(
            select(Step)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Step.stp_id == step_id,
                Step.stp_is_deleted.is_(False),
                Track.trk_is_deleted.is_(False),
                Track.trk_user_id == user_id,
            )
        )

    async def get(self, user_id: UUID, lesson_id: UUID) -> Lesson | None:
        result = await self.db.execute(
            select(Lesson)
            .join(Step, Step.stp_id == Lesson.lsn_step_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Lesson.lsn_id == lesson_id,
                Lesson.lsn_is_deleted.is_(False),
                Step.stp_is_deleted.is_(False),
                Track.trk_is_deleted.is_(False),
                Track.trk_user_id == user_id,
            )
            .options(*self._hierarchy_options())
        )
        return result.scalars().unique().one_or_none()

    async def position_exists(
        self,
        step_id: UUID,
        position: int,
        exclude_lesson_id: UUID | None = None,
    ) -> bool:
        filters = [
            Lesson.lsn_step_id == step_id,
            Lesson.lsn_position == position,
        ]
        if exclude_lesson_id is not None:
            filters.append(Lesson.lsn_id != exclude_lesson_id)
        lesson_id = await self.db.scalar(
            select(Lesson.lsn_id).where(*filters).limit(1)
        )
        return lesson_id is not None

    async def create(
        self,
        step_id: UUID,
        title: str,
        text: str,
        position: int,
    ) -> Lesson:
        lesson = Lesson(
            lsn_step_id=step_id,
            lsn_title=title,
            lsn_text=text,
            lsn_status=LessonStatusEnum.IDLE,
            lsn_position=position,
            lsn_is_deleted=False,
            lsn_deleted_at=None,
            feedbacks=[],
            lesson_files=[],
            quizzes=[],
        )
        self.db.add(lesson)
        await self.db.flush()
        return lesson

    async def list_by_step_id(
        self,
        user_id: UUID,
        step_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[list[Lesson], int]:
        filters = (
            Lesson.lsn_step_id == step_id,
            Lesson.lsn_is_deleted.is_(False),
            Step.stp_id == step_id,
            Step.stp_is_deleted.is_(False),
            Track.trk_is_deleted.is_(False),
            Track.trk_user_id == user_id,
        )
        total = await self.db.scalar(
            select(func.count())
            .select_from(Lesson)
            .join(Step, Step.stp_id == Lesson.lsn_step_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(*filters)
        )
        result = await self.db.execute(
            select(Lesson)
            .join(Step, Step.stp_id == Lesson.lsn_step_id)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(*filters)
            .order_by(Lesson.lsn_position.asc())
            .offset(offset)
            .limit(limit)
            .options(*self._hierarchy_options())
        )
        return list(result.scalars().unique().all()), int(total or 0)

    async def update(
        self,
        lesson: Lesson,
        title: str,
        text: str,
        status: LessonStatusEnum,
        position: int,
    ) -> Lesson:
        lesson.lsn_title = title
        lesson.lsn_text = text
        lesson.lsn_status = status
        lesson.lsn_position = position
        lesson.lsn_updated_at = datetime.now(UTC).replace(tzinfo=None)
        await self.db.flush()
        return lesson

    async def delete(self, lesson: Lesson) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        lesson.lsn_is_deleted = True
        lesson.lsn_deleted_at = now
        lesson.lsn_updated_at = now
        await self.db.flush()

    @staticmethod
    def _hierarchy_options():
        return (
            selectinload(
                Lesson.feedbacks.and_(Feedback.fbk_is_deleted.is_(False))
            ),
            selectinload(
                Lesson.lesson_files.and_(LessonFile.lsf_is_deleted.is_(False))
            ),
            selectinload(
                Lesson.quizzes.and_(Quiz.qui_is_deleted.is_(False))
            ).options(selectinload(Quiz.answers)),
        )


def get_lesson_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> LessonRepository:
    return LessonRepository(db)
