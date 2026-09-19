from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.models.feedback_model import Feedback
from sidebrain_back.models.lesson_file_model import LessonFile
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.mission_progress_model import MissionProgress
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track


class StepRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_accessible_track(
        self, user_id: UUID, track_id: UUID
    ) -> Track | None:
        result = await self.db.execute(
            select(Track).where(
                Track.trk_id == track_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self, track_id: UUID, level: StepLevelEnum, title: str
    ) -> Step:
        step = Step(
            stp_track_id=track_id,
            stp_level=level,
            stp_title=title,
            stp_is_deleted=False,
            stp_deleted_at=None,
            lessons=[],
            missions=[],
        )
        self.db.add(step)
        await self.db.flush()
        return step

    async def list(
        self, user_id: UUID, track_id: UUID, offset: int, limit: int
    ) -> tuple[list[Step], int]:
        filters = (
            Step.stp_track_id == track_id,
            Step.stp_is_deleted.is_(False),
            Track.trk_id == track_id,
            Track.trk_user_id == user_id,
            Track.trk_is_deleted.is_(False),
        )
        total = await self.db.scalar(
            select(func.count())
            .select_from(Step)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(*filters)
        )
        result = await self.db.execute(
            select(Step)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(*filters)
            .options(*self._hierarchy_options(user_id))
            .order_by(Step.stp_updated_at.desc(), Step.stp_id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().unique().all()), int(total or 0)

    async def get(
        self, user_id: UUID, track_id: UUID, step_id: UUID
    ) -> Step | None:
        result = await self.db.execute(
            select(Step)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Step.stp_id == step_id,
                Step.stp_track_id == track_id,
                Step.stp_is_deleted.is_(False),
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
            .options(*self._hierarchy_options(user_id))
        )
        return result.scalars().unique().one_or_none()

    async def update(
        self, step: Step, level: StepLevelEnum, title: str
    ) -> Step:
        step.stp_level = level
        step.stp_title = title
        step.stp_updated_at = datetime.now(UTC).replace(tzinfo=None)
        return step

    async def soft_delete(self, step: Step) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        step.stp_is_deleted = True
        step.stp_deleted_at = now
        step.stp_updated_at = now

    @staticmethod
    def _hierarchy_options(user_id: UUID):
        lessons = selectinload(
            Step.lessons.and_(Lesson.lsn_is_deleted.is_(False))
        ).options(
            selectinload(
                Lesson.lesson_files.and_(LessonFile.lsf_is_deleted.is_(False))
            ),
            selectinload(
                Lesson.feedbacks.and_(Feedback.fbk_is_deleted.is_(False))
            ),
            selectinload(
                Lesson.quizzes.and_(Quiz.qui_is_deleted.is_(False))
            ).options(selectinload(Quiz.answers)),
        )
        missions = selectinload(
            Step.missions.and_(Mission.msn_is_deleted.is_(False))
        ).options(
            selectinload(
                Mission.mission_progresses.and_(
                    MissionProgress.mpg_user_id == user_id
                )
            )
        )
        return lessons, missions


def get_step_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> StepRepository:
    return StepRepository(db)
