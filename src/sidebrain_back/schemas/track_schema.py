from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class TrackInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O título não pode ser vazio.")
        return value


class TrackCreate(TrackInput):
    pass


class TrackUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=255)
    description: str | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("O título não pode ser vazio.")
        return value

    @model_validator(mode="after")
    def require_field(self) -> "TrackUpdate":
        if not self.model_fields_set:
            raise ValueError("Ao menos um campo deve ser enviado.")
        return self


class PublicModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, extra="ignore"
    )


class AnswerResponse(PublicModel):
    id: UUID = Field(alias="ans_id", serialization_alias="id")
    text: str = Field(alias="ans_text", serialization_alias="text")
    rate: Any = Field(alias="ans_rate", serialization_alias="rate")
    created_at: datetime = Field(
        alias="ans_created_at", serialization_alias="created_at"
    )
    updated_at: datetime = Field(
        alias="ans_updated_at", serialization_alias="updated_at"
    )


class QuizResponse(PublicModel):
    id: UUID = Field(alias="qui_id", serialization_alias="id")
    question: str = Field(alias="qui_question", serialization_alias="question")
    updated_at: datetime = Field(
        alias="qui_updated_at", serialization_alias="updated_at"
    )
    answers: list[AnswerResponse] = []


class FeedbackResponse(PublicModel):
    id: UUID = Field(alias="fbk_id", serialization_alias="id")
    text: str = Field(alias="fbk_text", serialization_alias="text")
    created_at: datetime = Field(
        alias="fbk_created_at", serialization_alias="created_at"
    )
    updated_at: datetime = Field(
        alias="fbk_updated_at", serialization_alias="updated_at"
    )


class LessonFileResponse(PublicModel):
    id: UUID = Field(alias="lsf_id", serialization_alias="id")
    path: str = Field(alias="lsf_path", serialization_alias="path")
    file_type: Any = Field(
        alias="lsf_file_type", serialization_alias="file_type"
    )
    updated_at: datetime = Field(
        alias="lsf_updated_at", serialization_alias="updated_at"
    )


class LessonResponse(PublicModel):
    id: UUID = Field(alias="lsn_id", serialization_alias="id")
    title: str = Field(alias="lsn_title", serialization_alias="title")
    text: str = Field(alias="lsn_text", serialization_alias="text")
    status: Any = Field(alias="lsn_status", serialization_alias="status")
    position: int = Field(alias="lsn_position", serialization_alias="position")
    updated_at: datetime = Field(
        alias="lsn_updated_at", serialization_alias="updated_at"
    )
    lesson_files: list[LessonFileResponse] = []
    feedbacks: list[FeedbackResponse] = []
    quizzes: list[QuizResponse] = []


class MissionProgressResponse(PublicModel):
    id: UUID = Field(alias="mpg_id", serialization_alias="id")
    status: Any = Field(alias="mpg_status", serialization_alias="status")
    finished_in: datetime | None = Field(
        default=None,
        alias="mpg_finished_in",
        serialization_alias="finished_in",
    )
    score: int | None = Field(
        default=None, alias="mpg_score", serialization_alias="score"
    )
    updated_at: datetime = Field(
        alias="mpg_updated_at", serialization_alias="updated_at"
    )


class MissionResponse(PublicModel):
    id: UUID = Field(alias="msn_id", serialization_alias="id")
    title: str = Field(alias="msn_title", serialization_alias="title")
    difficulty: Any = Field(
        alias="msn_difficulty", serialization_alias="difficulty"
    )
    xp_reward: int = Field(
        alias="msn_xp_reward", serialization_alias="xp_reward"
    )
    criteria: Any = Field(alias="msn_criteria", serialization_alias="criteria")
    criteria_value: int = Field(
        alias="msn_criteria_value", serialization_alias="criteria_value"
    )
    updated_at: datetime = Field(
        alias="msn_updated_at", serialization_alias="updated_at"
    )
    mission_progresses: list[MissionProgressResponse] = []


class StepResponse(PublicModel):
    id: UUID = Field(alias="stp_id", serialization_alias="id")
    level: Any = Field(alias="stp_level", serialization_alias="level")
    title: str = Field(alias="stp_title", serialization_alias="title")
    status: Any = Field(alias="stp_status", serialization_alias="status")
    updated_at: datetime = Field(
        alias="stp_updated_at", serialization_alias="updated_at"
    )
    lessons: list[LessonResponse] = []
    missions: list[MissionResponse] = []


class TrackResponse(PublicModel):
    id: UUID = Field(alias="trk_id", serialization_alias="id")
    title: str = Field(alias="trk_title", serialization_alias="title")
    description: str | None = Field(
        default=None,
        alias="trk_description",
        serialization_alias="description",
    )
    created_at: datetime = Field(
        alias="trk_created_at", serialization_alias="created_at"
    )
    updated_at: datetime = Field(
        alias="trk_updated_at", serialization_alias="updated_at"
    )
    steps: list[StepResponse] = []
