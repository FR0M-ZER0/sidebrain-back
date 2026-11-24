from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator


class MentorConsentAccept(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, populate_by_name=True, extra="forbid"
    )

    notice_version: str = Field(min_length=1, max_length=64)
    accepted: StrictBool

    @field_validator("accepted")
    @classmethod
    def validate_accepted(cls, value: bool) -> bool:
        if not value:
            raise ValueError("A autorização deve ser aceita explicitamente")
        return value


class MentorConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    notice_version: str
    purpose: str
    recipient: str
    data_categories: list[str]
    retention_notice: str
    authorized: bool
    granted_at: datetime | None
