from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models.listing import ListingStatus
from app.schemas.category import CategoryRead
from app.schemas.common import BaseSchema, TimestampFields
from app.schemas.listing_image import ListingImageRead
from app.schemas.user import UserPublicRead


class ListingCreate(BaseSchema):
    category_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    price: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    city: str = Field(min_length=2, max_length=120)


class ListingUpdate(BaseSchema):
    category_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    status: ListingStatus | None = None


class ListingRead(BaseSchema, TimestampFields):
    id: int
    owner_id: int
    category_id: int
    title: str
    description: str
    price: Decimal
    currency: str
    city: str
    status: ListingStatus
    is_boosted: bool
    deleted_at: datetime | None


class ListingPublicRead(BaseSchema, TimestampFields):
    id: int
    title: str
    description: str
    price: Decimal
    currency: str
    city: str
    status: ListingStatus
    is_boosted: bool
    owner: UserPublicRead
    category: CategoryRead
    images: list[ListingImageRead] = []


class ListingWithOwnerRead(ListingRead):
    owner: UserPublicRead
    images: list[ListingImageRead] = []

