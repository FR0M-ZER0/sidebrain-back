from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sidebrain_back.schemas.pagination_schema import PaginationParams


class MentorConversationListParams(PaginationParams):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, extra="forbid"
    )

    track_id: UUID | None = None


class MentorConversationCreate(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, extra="forbid"
    )

    track_id: UUID


class MentorConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    track_id: UUID
    created_at: datetime
    updated_at: datetime


class MentorMessageCreate(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, extra="forbid"
    )

    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class MentorMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    sequence: int
    role: Literal["student", "mentor"]
    content: str
    created_at: datetime


class MentorGenerationAccepted(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    generation_id: UUID
    message_id: UUID
    status: Literal["queued", "processing", "completed", "failed"]


class MentorGenerationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    message_id: UUID
    status: Literal["queued", "processing", "completed", "failed"]
    response_message_id: UUID | None
    error_code: str | None


class MentorGenerationEvent(BaseModel):
    generation: MentorGenerationResponse
    message: MentorMessageResponse | None = None
