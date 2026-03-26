from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models.promotion import PromotionStatus, PromotionType
from app.schemas.common import BaseSchema, TimestampFields


class PromotionCreate(BaseSchema):
    listing_id: int = Field(gt=0)
    payment_id: int = Field(gt=0)
    promotion_type: PromotionType = PromotionType.BOOSTED
    target_city: str | None = Field(default=None, max_length=120)
    starts_at: datetime
    ends_at: datetime
    purchased_price: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class PromotionUpdate(BaseSchema):
    status: PromotionStatus | None = None


class PromotionRead(BaseSchema, TimestampFields):
    id: int
    user_id: int
    listing_id: int
    payment_id: int
    promotion_type: PromotionType
    status: PromotionStatus
    target_city: str | None
    starts_at: datetime
    ends_at: datetime
    purchased_price: Decimal
    currency: str


class PromotionActivateRequest(BaseSchema):
    payment_id: int = Field(gt=0)
    duration_days: int = Field(default=7, ge=1, le=365)
    target_city: str | None = Field(default=None, max_length=120)

