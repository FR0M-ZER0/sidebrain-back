from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sidebrain_back.models.answer_model import AnswerRateEnum


class QuizQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1000)

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class QuizCreateRequest(QuizQuestionRequest):
    pass


class QuizUpdateRequest(QuizQuestionRequest):
    pass


class PublicResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class AnswerResponse(PublicResponse):
    id: UUID = Field(validation_alias="ans_id")
    user_id: UUID = Field(validation_alias="ans_user_id")
    text: str = Field(validation_alias="ans_text")
    rate: AnswerRateEnum = Field(validation_alias="ans_rate")


class QuizResponse(PublicResponse):
    id: UUID = Field(validation_alias="qui_id")
    lesson_id: UUID = Field(validation_alias="qui_lesson_id")
    question: str = Field(validation_alias="qui_question")
    answers: list[AnswerResponse] = Field(default_factory=list)
