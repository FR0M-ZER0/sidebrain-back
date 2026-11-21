from collections import defaultdict
from datetime import UTC, datetime
from fractions import Fraction
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sidebrain_back.core.database import get_db
from sidebrain_back.core.errors import ProblemDetailError
from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.mission_criteria_enum import MissionCriteriaEnum
from sidebrain_back.enums.mission_progress_status_enum import (
    MissionProgressStatusEnum,
)
from sidebrain_back.models.mission_model import Mission
from sidebrain_back.models.mission_progress_model import MissionProgress
from sidebrain_back.repositories.mission_progress_repository import (
    LessonProgressFacts,
    MissionProgressRepository,
    get_mission_progress_repository,
)


class MissionProgressService:
    CORRECT_RATES = (AnswerRateEnum.GOOD, AnswerRateEnum.PERFECT)

    def __init__(
        self, repository: MissionProgressRepository, db: AsyncSession
    ):
        self.repository = repository
        self.db = db

    async def get_mission_track_for_quiz(
        self, user_id: UUID, quiz_id: UUID
    ) -> UUID:
        # Lock após a avaliação externa e antes de gravar a resposta.
        track_id = await self.repository.get_track_by_quiz_for_update(
            user_id, quiz_id
        )
        if track_id is None:
            raise ProblemDetailError(
                404, "Não encontrado", "Quiz não encontrado."
            )
        return track_id

    @staticmethod
    def _completed_lessons(lessons: list[LessonProgressFacts]) -> int:
        return sum(
            lesson.quizzes > 0 and lesson.answered == lesson.quizzes
            for lesson in lessons
        )

    @classmethod
    def _completed_step(cls, lessons: list[LessonProgressFacts]) -> bool:
        return bool(lessons) and cls._completed_lessons(lessons) == len(
            lessons
        )

    @classmethod
    def evaluate_mission(
        cls, mission: Mission, steps: dict[UUID, list[LessonProgressFacts]]
    ) -> tuple[MissionProgressStatusEnum, int]:
        lessons = steps.get(mission.msn_step_id, [])
        criteria = MissionCriteriaEnum(mission.msn_criteria)
        started = any(lesson.answered for lesson in lessons)
        if criteria == MissionCriteriaEnum.NUMBER_OF_LESSONS_COMPLETED:
            ratio = Fraction(
                cls._completed_lessons(lessons),
                max(mission.msn_criteria_value, 1),
            )
        elif criteria == MissionCriteriaEnum.COMPLETE_A_STEP:
            ratio = Fraction(
                cls._completed_lessons(lessons), len(lessons) or 1
            )
        elif criteria in (
            MissionCriteriaEnum.COMPLETE_A_TRACK,
            MissionCriteriaEnum.NUMBER_OF_STEPS_COMPLETED,
        ):
            completed = sum(
                cls._completed_step(items) for items in steps.values()
            )
            target = (
                len(steps)
                if criteria == MissionCriteriaEnum.COMPLETE_A_TRACK
                else mission.msn_criteria_value
            )
            ratio = Fraction(completed, max(target, 1))
            started = any(
                item.answered for items in steps.values() for item in items
            )
        elif criteria == MissionCriteriaEnum.GET_ALL_ANSWER_RIGHT_IN_A_LESSON:
            ratio = max(
                (
                    Fraction(item.correct, item.quizzes or 1)
                    for item in lessons
                ),
                default=Fraction(0),
            )
        else:  # GET_ALL_ANSWERS_RIGHT: somente os quizzes desta etapa.
            ratio = Fraction(
                sum(item.correct for item in lessons),
                sum(max(item.quizzes, 1) for item in lessons) or 1,
            )
        if ratio >= 1:
            return MissionProgressStatusEnum.DONE, 100
        status = (
            MissionProgressStatusEnum.IN_PROGRESS
            if started
            else MissionProgressStatusEnum.IDLE
        )
        return status, int(ratio * 100)

    async def update_missions_by_track_id(
        self, user_id: UUID, track_id: UUID
    ) -> None:
        """Recalcula na transação do chamador, sob lock da trilha."""
        facts = await self.repository.get_learning_facts(
            user_id, track_id, self.CORRECT_RATES
        )
        steps: dict[UUID, list[LessonProgressFacts]] = defaultdict(list)
        for fact in facts:
            lessons = steps[fact.step_id]
            if fact.lesson_id is not None:
                lessons.append(fact)
        now = datetime.now(UTC).replace(tzinfo=None)
        missions = await self.repository.list_missions_by_track_id(
            user_id, track_id
        )
        for mission in missions:
            progress = next(
                (
                    item
                    for item in mission.mission_progresses
                    if item.mpg_user_id == user_id
                ),
                None,
            )
            if (
                progress is not None
                and progress.mpg_status == MissionProgressStatusEnum.DONE
            ):
                continue
            status, score = self.evaluate_mission(mission, steps)
            if progress is None:
                progress = MissionProgress(
                    mpg_user_id=user_id, mpg_mission_id=mission.msn_id
                )
                mission.mission_progresses.append(progress)
                await self.repository.create(progress)
            elif (progress.mpg_status, progress.mpg_score) == (status, score):
                continue
            progress.mpg_status = status
            progress.mpg_score = score
            progress.mpg_updated_at = now
            progress.mpg_finished_in = (
                now if status == MissionProgressStatusEnum.DONE else None
            )
        await self.repository.flush()

    async def recalculate_missions_by_step_id(
        self, user_id: UUID, step_id: UUID
    ) -> None:
        try:
            track_id = await self.repository.get_track_by_step_for_update(
                user_id, step_id
            )
            if track_id is None:
                raise ProblemDetailError(
                    404, "Não encontrado", "Etapa não encontrada."
                )
            await self.update_missions_by_track_id(user_id, track_id)
            await self.db.commit()
        except ProblemDetailError:
            await self.db.rollback()
            raise
        except Exception as error:
            await self.db.rollback()
            raise ProblemDetailError(
                500,
                "Erro interno",
                "Não foi possível atualizar o progresso das missões.",
            ) from error


def get_mission_progress_service(
    repository: MissionProgressRepository = Depends(  # noqa: B008
        get_mission_progress_repository
    ),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> MissionProgressService:
    return MissionProgressService(repository, db)
