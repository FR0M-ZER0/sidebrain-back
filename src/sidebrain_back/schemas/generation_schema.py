from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.mission_criteria_enum import MissionCriteriaEnum
from sidebrain_back.enums.mission_difficulty_enum import MissionDifficultyEnum
from sidebrain_back.enums.step_level_enum import StepLevelEnum


def _required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("texto obrigatório")
    return value


class AssessmentAnswer(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    rate: AnswerRateEnum


class LearningContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    knowledge_level: StepLevelEnum | None = None
    assessment_answers: list[AssessmentAnswer] | None = None

    _validate_goal = field_validator("goal", "topic")(_required_text)


class GenerationInput(LearningContext):
    request_id: UUID
    user_id: UUID


class GeneratedQuiz(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1)

    _validate_question = field_validator("question")(_required_text)


class GeneratedLesson(BaseModel):
    model_config = ConfigDict(extra="forbid")
    position: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1)
    quiz: GeneratedQuiz

    _validate_title = field_validator("title", "text")(_required_text)


class GeneratedMission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)
    difficulty: MissionDifficultyEnum
    xp_reward: int = Field(gt=0)
    criteria: MissionCriteriaEnum
    criteria_value: int = Field(gt=0)

    _validate_title = field_validator("title")(_required_text)


class GeneratedStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    position: int = Field(gt=0)
    level: StepLevelEnum
    title: str = Field(min_length=1, max_length=255)
    lessons: list[GeneratedLesson] = Field(default_factory=list)
    mission: GeneratedMission | None = None

    _validate_title = field_validator("title")(_required_text)


class GeneratedTrack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    steps: list[GeneratedStep] = Field(min_length=1)

    _validate_text = field_validator("title", "description")(_required_text)

    @model_validator(mode="after")
    def validate_structure(self) -> "GeneratedTrack":
        positions = [step.position for step in self.steps]
        if positions != list(range(1, len(positions) + 1)):
            raise ValueError("etapas devem ter posições contíguas")
        levels = [step.level for step in self.steps]
        if levels != list(dict.fromkeys(levels)):
            raise ValueError("níveis das etapas não podem duplicar")
        for step in self.steps:
            lesson_positions = [lesson.position for lesson in step.lessons]
            if step.position != 1 and (step.lessons or step.mission):
                raise ValueError("etapas futuras não podem ter conteúdo")
            if lesson_positions != list(
                range(1, len(lesson_positions) + 1)
            ):
                raise ValueError("lições devem ter posições contíguas")
        return self


class GenerationSuccess(BaseModel):
    status: str = "succeeded"
    request_id: UUID
    track_id: UUID


class GenerationFailure(BaseModel):
    status: str = "failed"
    request_id: UUID
    error_code: str
    detail: str = "Não foi possível gerar a trilha."
