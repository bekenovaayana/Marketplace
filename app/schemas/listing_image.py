from __future__ import annotations

from pydantic import Field, HttpUrl

from app.schemas.common import BaseSchema, TimestampFields


class ListingImageCreate(BaseSchema):
    url: HttpUrl
    sort_order: int = Field(default=0, ge=0)


class ListingImageUpdate(BaseSchema):
    url: HttpUrl | None = None
    sort_order: int | None = Field(default=None, ge=0)


class ListingImageRead(BaseSchema, TimestampFields):
    id: int
    listing_id: int
    url: str
    sort_order: int

