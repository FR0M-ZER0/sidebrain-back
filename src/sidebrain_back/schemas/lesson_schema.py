from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sidebrain_back.enums.answer_rate_enum import AnswerRateEnum
from sidebrain_back.enums.lesson_file_type_enum import LessonFileTypeEnum
from sidebrain_back.enums.lesson_status_enum import LessonStatusEnum


class LessonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1)
    position: int = Field(ge=1)

    @field_validator("title", "text", mode="before")
    @classmethod
    def strip_text_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class LessonCreateRequest(LessonInput):
    pass


class LessonUpdateRequest(LessonInput):
    status: LessonStatusEnum


class LessonPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class LessonAnswerResponse(LessonPublicResponse):
    id: UUID = Field(validation_alias="ans_id")
    user_id: UUID = Field(validation_alias="ans_user_id")
    text: str = Field(validation_alias="ans_text")
    rate: AnswerRateEnum = Field(validation_alias="ans_rate")
    created_at: datetime = Field(validation_alias="ans_created_at")
    updated_at: datetime = Field(validation_alias="ans_updated_at")


class LessonQuizResponse(LessonPublicResponse):
    id: UUID = Field(validation_alias="qui_id")
    question: str = Field(validation_alias="qui_question")
    updated_at: datetime = Field(validation_alias="qui_updated_at")
    answers: list[LessonAnswerResponse] = Field(default_factory=list)


class LessonFileResponse(LessonPublicResponse):
    id: UUID = Field(validation_alias="lsf_id")
    path: str = Field(validation_alias="lsf_path")
    file_type: LessonFileTypeEnum = Field(validation_alias="lsf_file_type")
    updated_at: datetime = Field(validation_alias="lsf_updated_at")


class LessonFeedbackResponse(LessonPublicResponse):
    id: UUID = Field(validation_alias="fbk_id")
    user_id: UUID = Field(validation_alias="fbk_user_id")
    text: str = Field(validation_alias="fbk_text")
    created_at: datetime = Field(validation_alias="fbk_created_at")
    updated_at: datetime = Field(validation_alias="fbk_updated_at")


class LessonResponse(LessonPublicResponse):
    id: UUID = Field(validation_alias="lsn_id")
    title: str = Field(validation_alias="lsn_title")
    text: str = Field(validation_alias="lsn_text")
    status: LessonStatusEnum = Field(validation_alias="lsn_status")
    position: int = Field(validation_alias="lsn_position")
    updated_at: datetime = Field(validation_alias="lsn_updated_at")
    feedbacks: list[LessonFeedbackResponse] = Field(default_factory=list)
    files: list[LessonFileResponse] = Field(
        default_factory=list,
        validation_alias="lesson_files",
    )
    quizzes: list[LessonQuizResponse] = Field(default_factory=list)
