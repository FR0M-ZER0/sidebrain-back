from pydantic import BaseModel, ConfigDict, Field


class AvatarResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    slug: str = Field(validation_alias="avt_slug")
    name: str = Field(validation_alias="avt_name")
    image_url: str = Field(
        validation_alias="avt_image_path",
        serialization_alias="imageUrl",
    )


class AvatarListResponse(BaseModel):
    data: list[AvatarResponse]
