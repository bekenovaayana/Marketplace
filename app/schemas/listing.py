from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import Field, field_validator, model_validator

from app.models.listing import ListingStatus
from app.schemas.category import CategoryRead
from app.schemas.common import BaseSchema, TimestampFields
from app.schemas.listing_image import ListingImageCreate, ListingImageRead
from app.schemas.user import UserPublicRead


class ListingCreate(BaseSchema):
    category_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    price: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    city: str = Field(min_length=2, max_length=120)
    contact_phone: str = Field(min_length=6, max_length=32)
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))
    images: list[ListingImageCreate] = Field(default_factory=list, max_length=10)

    @field_validator("contact_phone")
    @classmethod
    def validate_contact_phone(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("contact_phone is required")
        allowed_chars = set("0123456789+ -()")
        if any(ch not in allowed_chars for ch in normalized):
            raise ValueError("contact_phone contains invalid characters")
        return normalized


class ListingDraftCreate(BaseSchema):
    category_id: int | None = Field(default=None, gt=0, description="Optional for draft, required on publish")
    title: str | None = Field(default=None, min_length=3, max_length=200, description="Optional for draft")
    description: str | None = Field(default=None, min_length=10, description="Optional for draft")
    price: Decimal | None = Field(default=None, ge=0, description="Optional for draft")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    city: str | None = Field(default=None, min_length=2, max_length=120, description="Optional for draft")
    contact_phone: str | None = Field(default=None, min_length=6, max_length=32, description="Optional for draft")
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))
    images: list[ListingImageCreate] = Field(default_factory=list, max_length=10)

    @field_validator("contact_phone")
    @classmethod
    def validate_draft_contact_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        if not normalized:
            return None
        allowed_chars = set("0123456789+ -()")
        if any(ch not in allowed_chars for ch in normalized):
            raise ValueError("contact_phone contains invalid characters")
        return normalized


class ListingUpdate(BaseSchema):
    category_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    contact_phone: str | None = Field(default=None, min_length=6, max_length=32)
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))
    images: list[ListingImageCreate] | None = Field(default=None, max_length=10)
    status: ListingStatus | None = None

    @field_validator("contact_phone")
    @classmethod
    def validate_contact_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("contact_phone cannot be empty")
        allowed_chars = set("0123456789+ -()")
        if any(ch not in allowed_chars for ch in normalized):
            raise ValueError("contact_phone contains invalid characters")
        return normalized


class ListingImageReorderRequest(BaseSchema):
    images: list[ListingImageCreate] = Field(
        max_length=10,
        description="Reordered listing images. Accepts either {'images': [...]} or root array payload.",
        examples=[
            [{"url": "http://localhost:8000/uploads/listings/a.png", "sort_order": 0}],
            {"images": [{"url": "http://localhost:8000/uploads/listings/a.png", "sort_order": 0}]},
        ],
    )

    @model_validator(mode="before")
    @classmethod
    def allow_root_array_payload(cls, data: object) -> object:
        if isinstance(data, list):
            return {"images": data}
        return data


class ListingMyStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SOLD = "sold"


class PublishListingResponse(BaseSchema):
    detail: str
    listing: "ListingWithOwnerRead"


class ListingRead(BaseSchema, TimestampFields):
    id: int
    owner_id: int
    category_id: int | None
    title: str | None
    description: str | None
    price: Decimal | None
    currency: str
    city: str | None
    contact_phone: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    status: ListingStatus
    is_boosted: bool
    view_count: int = 0
    deleted_at: datetime | None


class ListingPublicRead(BaseSchema, TimestampFields):
    id: int
    title: str
    description: str
    price: Decimal
    currency: str
    city: str
    contact_phone: str
    latitude: Decimal | None
    longitude: Decimal | None
    status: ListingStatus
    is_boosted: bool
    view_count: int = 0
    owner: UserPublicRead
    category: CategoryRead
    images: list[ListingImageRead] = []


class ListingWithOwnerRead(ListingRead):
    owner: UserPublicRead
    images: list[ListingImageRead] = []

