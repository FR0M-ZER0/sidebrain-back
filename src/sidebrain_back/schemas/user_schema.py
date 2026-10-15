from typing import Annotated
from uuid import UUID

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

Name = Annotated[str, Field(min_length=1, max_length=255)]
Password = Annotated[str, Field(min_length=8)]


def _normalize_name(value: str | None) -> str | None:
    return value.strip() if value is not None else None


def _normalize_email(value: str | None) -> str | None:
    return value.strip().lower() if value is not None else None


class UserRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    email: Annotated[EmailStr, Field(max_length=255)]
    password: Password

    _trim_name = field_validator("name", mode="before")(_normalize_name)
    _normalize_email = field_validator("email", mode="before")(
        _normalize_email
    )


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    email: Annotated[EmailStr, Field(max_length=255)] | None = None

    _trim_name = field_validator("name", mode="before")(_normalize_name)
    _normalize_email = field_validator("email", mode="before")(
        _normalize_email
    )

    @model_validator(mode="after")
    def require_change(self) -> "UserUpdateRequest":
        if self.name is None and self.email is None:
            raise ValueError("Informe nome e/ou e-mail.")
        return self


class PasswordUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    current_password: str = Field(alias="currentPassword")
    new_password: Password = Field(alias="newPassword")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(
        validation_alias=AliasChoices("id", "usr_id"),
        serialization_alias="id",
    )
    name: str = Field(
        validation_alias=AliasChoices("name", "usr_name"),
        serialization_alias="name",
    )
    email: EmailStr = Field(
        validation_alias=AliasChoices("email", "usr_email"),
        serialization_alias="email",
    )
