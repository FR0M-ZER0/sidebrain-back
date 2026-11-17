from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from sidebrain_back.schemas.pagination_schema import PaginatedResponse


class RankingEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    position: int = Field(..., ge=1)
    user_id: UUID = Field(
        ...,
        alias="userId",
        serialization_alias="userId",
    )
    name: str
    xp: int = Field(..., ge=0)
    missions_completed: int = Field(
        ...,
        ge=0,
        alias="missionsCompleted",
        serialization_alias="missionsCompleted",
    )


RankingListResponse = PaginatedResponse[RankingEntryResponse]
