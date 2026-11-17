from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from sidebrain_back.schemas.user_schema import UserResponse, _normalize_email


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=255)
    password: str

    _normalize_email = field_validator("email", mode="before")(
        _normalize_email
    )


class AuthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    token_type: Literal["Bearer"] = Field(
        default="Bearer",
        alias="tokenType",
    )
    user: UserResponse
