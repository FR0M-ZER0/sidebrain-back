from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sidebrain_back.core.database import get_db
from sidebrain_back.models.feedback_model import Feedback
from sidebrain_back.models.lesson_file_model import LessonFile
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.mission_progress_model import MissionProgress
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track
from sidebrain_back.models.user_model import User


@dataclass(frozen=True)
class StepProgressContext:
    active_lessons_total: int
    active_lessons_completed: int
    completion_ratio: float


class TrackRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self, user: User, title: str, description: str | None
    ) -> Track:
        track = Track(
            trk_user_id=user.usr_id,
            trk_title=title,
            trk_description=description,
            trk_is_deleted=False,
            trk_deleted_at=None,
            steps=[],
        )
        self.db.add(track)
        await self.db.flush()
        return track

    async def list(
        self, user_id: UUID, offset: int, limit: int
    ) -> tuple[list[Track], int]:
        filters = (
            Track.trk_user_id == user_id,
            Track.trk_is_deleted.is_(False),
        )
        total = await self.db.scalar(
            select(func.count()).select_from(Track).where(*filters)
        )
        result = await self.db.execute(
            select(Track)
            .where(*filters)
            .order_by(Track.trk_created_at.desc(), Track.trk_id.desc())
            .offset(offset)
            .limit(limit)
            .options(self._hierarchy_options(user_id))
        )
        return list(result.scalars().unique().all()), int(total or 0)

    async def get(self, user_id: UUID, track_id: UUID) -> Track | None:
        result = await self.db.execute(
            select(Track)
            .where(
                Track.trk_id == track_id,
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
            .options(self._hierarchy_options(user_id))
        )
        return result.scalars().unique().one_or_none()

    async def update(
        self,
        track: Track,
        title: str | None,
        description: str | None,
        update_description: bool,
    ) -> Track:
        now = datetime.now(UTC).replace(tzinfo=None)
        if title is not None:
            track.trk_title = title
        if update_description:
            track.trk_description = description
        track.trk_updated_at = now
        return track

    async def soft_delete(self, track: Track) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        track.trk_is_deleted = True
        track.trk_deleted_at = now
        track.trk_updated_at = now

    async def get_step_progress(self, step_id: UUID) -> StepProgressContext:
        filters = (
            Lesson.lsn_step_id == step_id,
            Lesson.lsn_is_deleted.is_(False),
            Step.stp_is_deleted.is_(False),
            Track.trk_is_deleted.is_(False),
        )
        total = int(
            await self.db.scalar(
                select(func.count())
                .select_from(Lesson)
                .join(Step, Step.stp_id == Lesson.lsn_step_id)
                .join(Track, Track.trk_id == Step.stp_track_id)
                .where(*filters)
            )
            or 0
        )
        completed = int(
            await self.db.scalar(
                select(func.count())
                .select_from(Lesson)
                .join(Step, Step.stp_id == Lesson.lsn_step_id)
                .join(Track, Track.trk_id == Step.stp_track_id)
                .where(*filters, Lesson.lsn_status == "done")
            )
            or 0
        )
        return StepProgressContext(
            active_lessons_total=total,
            active_lessons_completed=completed,
            completion_ratio=completed / total if total else 0.0,
        )

    async def get_active_step_for_user(
        self, track_id: UUID, step_id: UUID, user_id: UUID
    ) -> Step | None:
        return await self.db.scalar(
            select(Step)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Step.stp_id == step_id,
                Step.stp_track_id == track_id,
                Step.stp_is_deleted.is_(False),
                Track.trk_user_id == user_id,
                Track.trk_is_deleted.is_(False),
            )
        )

    async def get_next_eligible_step(self, step_id: UUID) -> Step | None:
        current = await self.db.scalar(
            select(Step)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Step.stp_id == step_id,
                Step.stp_is_deleted.is_(False),
                Track.trk_is_deleted.is_(False),
            )
        )
        if current is None:
            return None

        steps = await self.db.scalars(
            select(Step)
            .where(
                Step.stp_track_id == current.stp_track_id,
                Step.stp_is_deleted.is_(False),
            )
            .options(
                selectinload(
                    Step.lessons.and_(Lesson.lsn_is_deleted.is_(False))
                ),
                selectinload(
                    Step.missions.and_(Mission.msn_is_deleted.is_(False))
                ),
            )
            .order_by(Step.stp_updated_at, Step.stp_id)
        )
        ordered_steps = list(steps.all())
        try:
            current_index = next(
                index
                for index, candidate in enumerate(ordered_steps)
                if candidate.stp_id == current.stp_id
            )
        except StopIteration:
            return None

        for candidate in ordered_steps[current_index + 1 :]:
            if not candidate.lessons and not candidate.missions:
                return candidate
        return None

    async def get_step_for_generation(self, step_id: UUID) -> Step | None:
        result = await self.db.execute(
            select(Step)
            .join(Track, Track.trk_id == Step.stp_track_id)
            .where(
                Step.stp_id == step_id,
                Step.stp_is_deleted.is_(False),
                Track.trk_is_deleted.is_(False),
            )
            .options(
                selectinload(Step.track).options(
                    selectinload(
                        Track.steps.and_(Step.stp_is_deleted.is_(False))
                    ).options(
                        selectinload(
                            Step.lessons.and_(Lesson.lsn_is_deleted.is_(False))
                        )
                    )
                ),
                selectinload(
                    Step.lessons.and_(Lesson.lsn_is_deleted.is_(False))
                ),
                selectinload(
                    Step.missions.and_(Mission.msn_is_deleted.is_(False))
                ),
            )
            .with_for_update()
        )
        return result.scalars().unique().one_or_none()

    async def has_active_generated_content(self, step_id: UUID) -> bool:
        lesson_exists = await self.db.scalar(
            select(Lesson.lsn_id)
            .where(
                Lesson.lsn_step_id == step_id,
                Lesson.lsn_is_deleted.is_(False),
            )
            .limit(1)
        )
        mission_exists = await self.db.scalar(
            select(Mission.msn_id)
            .where(
                Mission.msn_step_id == step_id,
                Mission.msn_is_deleted.is_(False),
            )
            .limit(1)
        )
        return lesson_exists is not None or mission_exists is not None

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
        return selectinload(
            Track.steps.and_(Step.stp_is_deleted.is_(False))
        ).options(lessons, missions)


def get_track_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TrackRepository:
    return TrackRepository(db)
