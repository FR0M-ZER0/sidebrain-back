from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O texto não pode ser vazio.")
        return value


class FeedbackUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O texto não pode ser vazio.")
        return value

    @model_validator(mode="after")
    def require_field(self) -> "FeedbackUpdate":
        if not self.model_fields_set:
            raise ValueError("Ao menos um campo deve ser enviado.")
        return self


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(alias="fbk_id", serialization_alias="id")
    lesson_id: UUID = Field(
        alias="fbk_lesson_id", serialization_alias="lesson_id"
    )
    author_id: UUID = Field(
        alias="fbk_user_id", serialization_alias="author_id"
    )
    text: str = Field(alias="fbk_text", serialization_alias="text")
    created_at: datetime = Field(
        alias="fbk_created_at", serialization_alias="created_at"
    )
    updated_at: datetime = Field(
        alias="fbk_updated_at", serialization_alias="updated_at"
    )
