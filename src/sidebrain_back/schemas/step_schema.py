from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from sidebrain_back.enums.step_level_enum import StepLevelEnum
from sidebrain_back.schemas.track_schema import (
    LessonResponse,
    MissionResponse,
    PublicModel,
)


class StepInput(PublicModel):
    model_config = ConfigDict(extra="forbid")

    level: StepLevelEnum
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O título não pode ser vazio.")
        return value


class StepCreate(StepInput):
    pass


class StepUpdate(StepInput):
    pass


class StepResponse(PublicModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, extra="ignore"
    )

    id: UUID = Field(alias="stp_id", serialization_alias="id")
    level: Any = Field(alias="stp_level", serialization_alias="level")
    title: str = Field(alias="stp_title", serialization_alias="title")
    status: Any = Field(alias="stp_status", serialization_alias="status")
    updated_at: datetime = Field(
        alias="stp_updated_at", serialization_alias="updated_at"
    )
    lessons: list[LessonResponse] = Field(default_factory=list)
    missions: list[MissionResponse] = Field(default_factory=list)
