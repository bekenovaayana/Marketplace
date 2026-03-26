from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampFields


class CategoryCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=140, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    is_active: bool = True
    display_order: int = Field(default=0, ge=0)


class CategoryUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=140, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    is_active: bool | None = None
    display_order: int | None = Field(default=None, ge=0)


class CategoryRead(BaseSchema, TimestampFields):
    id: int
    name: str
    slug: str
    is_active: bool
    display_order: int

