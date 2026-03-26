from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models.payment import PaymentStatus
from app.schemas.common import BaseSchema, TimestampFields


class PaymentCreate(BaseSchema):
    listing_id: int = Field(gt=0)
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class PaymentUpdate(BaseSchema):
    status: PaymentStatus | None = None


class PaymentRead(BaseSchema, TimestampFields):
    id: int
    user_id: int
    listing_id: int
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: str
    provider_reference: str | None
    paid_at: datetime | None

