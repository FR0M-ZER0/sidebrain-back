from datetime import datetime
from uuid import UUID

from pydantic import (
    AliasChoices,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from sidebrain_back.enums.mission_criteria_enum import MissionCriteriaEnum
from sidebrain_back.enums.mission_difficulty_enum import MissionDifficultyEnum
from sidebrain_back.schemas.track_schema import PublicModel


class MissionCreate(PublicModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
    )

    title: str = Field(min_length=1, max_length=255)
    difficulty: MissionDifficultyEnum
    xp_reward: int = Field(alias="xpReward", ge=0)
    criteria: MissionCriteriaEnum
    criteria_value: int = Field(alias="criteriaValue", gt=0)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O título não pode ser vazio.")
        return value


class MissionUpdate(PublicModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
    )

    title: str | None = Field(default=None, min_length=1, max_length=255)
    difficulty: MissionDifficultyEnum | None = None
    xp_reward: int | None = Field(default=None, alias="xpReward", ge=0)
    criteria: MissionCriteriaEnum | None = None
    criteria_value: int | None = Field(
        default=None, alias="criteriaValue", gt=0
    )

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
    def require_field(self) -> "MissionUpdate":
        if not self.model_fields_set:
            raise ValueError("Ao menos um campo deve ser enviado.")
        return self


class MissionProgressPublicResponse(PublicModel):
    id: UUID = Field(validation_alias="mpg_id")
    status: str = Field(validation_alias="mpg_status")
    finished_in: datetime | None = Field(
        default=None, validation_alias="mpg_finished_in"
    )
    score: int | None = Field(default=None, validation_alias="mpg_score")
    updated_at: datetime = Field(validation_alias="mpg_updated_at")


class MissionResponse(PublicModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="ignore",
    )

    id: UUID = Field(validation_alias="msn_id")
    step_id: UUID = Field(
        alias="stepId",
        validation_alias=AliasChoices("msn_step_id", "stepId"),
        serialization_alias="stepId",
    )
    title: str = Field(validation_alias="msn_title")
    difficulty: MissionDifficultyEnum = Field(
        validation_alias="msn_difficulty"
    )
    xp_reward: int = Field(
        alias="xpReward",
        validation_alias=AliasChoices("msn_xp_reward", "xpReward"),
        serialization_alias="xpReward",
    )
    criteria: MissionCriteriaEnum = Field(validation_alias="msn_criteria")
    criteria_value: int = Field(
        alias="criteriaValue",
        validation_alias=AliasChoices("msn_criteria_value", "criteriaValue"),
        serialization_alias="criteriaValue",
    )
    updated_at: datetime = Field(
        alias="updatedAt",
        validation_alias=AliasChoices("msn_updated_at", "updatedAt"),
        serialization_alias="updatedAt",
    )
    mission_progresses: list[MissionProgressPublicResponse] = Field(
        default_factory=list,
        alias="missionProgresses",
        validation_alias=AliasChoices(
            "mission_progresses", "missionProgresses"
        ),
        serialization_alias="missionProgresses",
    )
