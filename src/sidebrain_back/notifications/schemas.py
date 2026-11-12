from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    data: dict[str, Any]
