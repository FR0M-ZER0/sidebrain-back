from sidebrain_back.enums.mission_criteria_enum import MissionCriteriaEnum
from sidebrain_back.schemas.generation_schema import GeneratedTrack


class MissionGenerationService:
    MAX_TITLE_LENGTH = 255

    @staticmethod
    def build_measurable_title(
        criteria: MissionCriteriaEnum,
        criteria_value: int,
        *,
        step_title: str | None = None,
        track_title: str | None = None,
    ) -> str:
        scope_title = None
        if criteria is MissionCriteriaEnum.NUMBER_OF_LESSONS_COMPLETED:
            lesson_word = "lição" if criteria_value == 1 else "lições"
            title = f"Conclua {criteria_value} {lesson_word} da etapa"
            scope_title = step_title
        elif criteria is MissionCriteriaEnum.NUMBER_OF_STEPS_COMPLETED:
            step_word = "etapa" if criteria_value == 1 else "etapas"
            title = f"Conclua {criteria_value} {step_word} da trilha"
            scope_title = track_title
        elif criteria is MissionCriteriaEnum.GET_ALL_ANSWER_RIGHT_IN_A_LESSON:
            title = "Acerte todas as respostas de uma lição"
            scope_title = step_title
        elif criteria is MissionCriteriaEnum.COMPLETE_A_STEP:
            title = "Conclua a etapa"
            scope_title = step_title
        elif criteria is MissionCriteriaEnum.COMPLETE_A_TRACK:
            title = "Conclua a trilha"
            scope_title = track_title
        elif criteria is MissionCriteriaEnum.GET_ALL_ANSWERS_RIGHT:
            title = "Acerte todas as respostas dos quizzes"
            scope_title = step_title
        else:
            raise ValueError(f"Critério de missão não suportado: {criteria}")
        if scope_title:
            title = f"{title}: {scope_title.strip()}"
        return title[: MissionGenerationService.MAX_TITLE_LENGTH].rstrip()

    @classmethod
    def align_track_mission_titles(cls, track: GeneratedTrack) -> None:
        for step in track.steps:
            if step.mission is not None:
                step.mission.title = cls.build_measurable_title(
                    step.mission.criteria,
                    step.mission.criteria_value,
                    step_title=step.title,
                    track_title=track.title,
                )
