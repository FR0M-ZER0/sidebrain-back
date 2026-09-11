from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

ItemT = TypeVar("ItemT")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[ItemT]):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    data: list[ItemT]
    page: int
    page_size: int
    total_items: int
    total_pages: int

    @classmethod
    def build(
        cls,
        data: list[ItemT],
        page: int,
        page_size: int,
        total_items: int,
    ) -> "PaginatedResponse[ItemT]":
        return cls(
            data=data,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=ceil(total_items / page_size) if total_items else 0,
        )
