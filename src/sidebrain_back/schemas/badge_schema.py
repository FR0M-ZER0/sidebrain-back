from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from sidebrain_back.enums.badge_criteria_enum import BadgeCriteriaEnum
from sidebrain_back.enums.badge_progress_status_enum import (
    BadgeProgressStatusEnum,
)
from sidebrain_back.enums.badge_rarity_enum import BadgeRarityEnum


class BadgeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    rarity: BadgeRarityEnum
    criteria: BadgeCriteriaEnum
    criteria_value: int = Field(gt=0)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class BadgeCreate(BadgeInput):
    pass


class BadgeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    rarity: BadgeRarityEnum | None = None
    criteria: BadgeCriteriaEnum | None = None
    criteria_value: int | None = Field(default=None, gt=0)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_editable_field(self) -> "BadgeUpdate":
        if not self.model_fields_set:
            raise ValueError("Ao menos um campo deve ser informado.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("O nome não pode ser nulo.")
        return self


class BadgeProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(validation_alias="bpg_id")
    status: BadgeProgressStatusEnum = Field(validation_alias="bpg_status")
    updated_at: datetime = Field(validation_alias="bpg_updated_at")


class BadgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(validation_alias="bdg_id")
    name: str = Field(validation_alias="bdg_name")
    description: str | None = Field(validation_alias="bdg_description")
    rarity: BadgeRarityEnum = Field(validation_alias="bdg_rarity")
    criteria: BadgeCriteriaEnum = Field(validation_alias="bdg_criteria")
    criteria_value: int = Field(validation_alias="bdg_criteria_value")
    updated_at: datetime = Field(validation_alias="bdg_updated_at")
    progress: list[BadgeProgressResponse] = Field(
        default_factory=list,
        validation_alias="badge_progresses",
    )
