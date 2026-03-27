from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampFields:
    created_at: datetime
    updated_at: datetime


T = TypeVar("T")


class PageMeta(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class Page(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta
    page: int | None = None
    page_size: int | None = None
    total_items: int | None = None
    total_pages: int | None = None
    facets: dict | None = None

    @model_validator(mode="after")
    def sync_flat_pagination_fields(self) -> "Page[T]":
        self.page = self.meta.page
        self.page_size = self.meta.page_size
        self.total_items = self.meta.total_items
        self.total_pages = self.meta.total_pages
        return self

