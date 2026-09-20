from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum
from sidebrain_back.enums.step_status_enum import StepStatusEnum
from sidebrain_back.models.lesson_model import Lesson
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.quiz_model import Quiz
from sidebrain_back.models.step_model import Step
from sidebrain_back.models.track_model import Track
from sidebrain_back.schemas.generation_schema import GeneratedTrack


class GenerationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_request_id(self, request_id: UUID) -> Track | None:
        result = await self.db.execute(
            select(Track).where(
                Track.trk_generation_request_id == request_id,
                Track.trk_is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self, user_id: UUID, request_id: UUID, generated: GeneratedTrack
    ) -> Track:
        track = Track(
            trk_user_id=user_id,
            trk_generation_request_id=request_id,
            trk_title=generated.title,
            trk_description=generated.description,
            trk_is_deleted=False,
        )
        self.db.add(track)
        await self.db.flush()
        for generated_step in generated.steps:
            step = Step(
                stp_track_id=track.trk_id,
                stp_level=generated_step.level,
                stp_title=generated_step.title,
                stp_status=StepStatusEnum.IDLE,
                stp_is_deleted=False,
            )
            self.db.add(step)
            await self.db.flush()
            if generated_step.position != 1:
                continue
            for generated_lesson in generated_step.lessons:
                lesson = Lesson(
                    lsn_step_id=step.stp_id,
                    lsn_title=generated_lesson.title,
                    lsn_text=generated_lesson.text,
                    lsn_position=generated_lesson.position,
                    lsn_status=LessonStatusEnum.IDLE,
                    lsn_is_deleted=False,
                )
                self.db.add(lesson)
                await self.db.flush()
                self.db.add(
                    Quiz(
                        qui_lesson_id=lesson.lsn_id,
                        qui_question=generated_lesson.quiz.question,
                    )
                )
            if generated_step.mission:
                mission = generated_step.mission
                self.db.add(
                    Mission(
                        msn_step_id=step.stp_id,
                        msn_title=mission.title,
                        msn_difficulty=mission.difficulty,
                        msn_xp_reward=mission.xp_reward,
                        msn_criteria=mission.criteria,
                        msn_criteria_value=mission.criteria_value,
                        msn_is_deleted=False,
                    )
                )
        return track
