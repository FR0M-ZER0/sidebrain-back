from pydantic import BaseModel, ConfigDict, Field


class UserStatisticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    xp: int = Field(..., ge=0)
    missions_completed: int = Field(
        ...,
        ge=0,
        alias="missionsCompleted",
        serialization_alias="missionsCompleted",
    )
    position: int = Field(..., ge=1)
    badges_unlocked: int = Field(
        ...,
        ge=0,
        alias="badgesUnlocked",
        serialization_alias="badgesUnlocked",
    )
    current_day_streak: int = Field(
        ...,
        ge=0,
        alias="currentDayStreak",
        serialization_alias="currentDayStreak",
    )
