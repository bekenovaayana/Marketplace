from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models.promotion import PromotionStatus, PromotionType
from app.schemas.common import BaseSchema, TimestampFields


class PromotionRead(BaseSchema, TimestampFields):
    id: int
    user_id: int
    listing_id: int
    payment_id: int
    promotion_type: PromotionType
    status: PromotionStatus
    days: int = Field(ge=1, le=365)
    target_city: str | None
    starts_at: datetime
    ends_at: datetime
    amount: Decimal = Field(ge=0)
    currency: str
    payment_provider: str | None = None
    payment_intent_id: str | None = None


class PromotionOption(BaseSchema):
    days: int = Field(ge=1, le=365)
    price: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class PromotionOptionsResponse(BaseSchema):
    currency: str = Field(default="USD", min_length=3, max_length=3)
    price_per_day: Decimal = Field(ge=0)
    options: list[PromotionOption]


class PromotionCheckoutRequest(BaseSchema):
    listing_id: int = Field(gt=0)
    days: int = Field(ge=1, le=365)


class PromotionCheckoutResponse(BaseSchema):
    promotion_id: int
    payment_provider: str
    payment_intent_id: str
    amount: Decimal
    currency: str
    checkout_url: str | None = None
    client_secret: str | None = None


class PromotionWebhookRequest(BaseSchema):
    payment_provider: str
    payment_intent_id: str
    event: str = Field(description="e.g. payment_succeeded or payment_failed")

