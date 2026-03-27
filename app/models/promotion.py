from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PromotionStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PromotionType(str, enum.Enum):
    BOOSTED = "boosted"


class Promotion(Base, TimestampMixin):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"), nullable=False, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)

    promotion_type: Mapped[PromotionType] = mapped_column(
        Enum(
            PromotionType,
            name="promotion_type",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        server_default=PromotionType.BOOSTED.value,
    )
    status: Mapped[PromotionStatus] = mapped_column(
        Enum(
            PromotionStatus,
            name="promotion_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        server_default=PromotionStatus.PENDING_PAYMENT.value,
        index=True,
    )

    days: Mapped[int] = mapped_column(nullable=False, server_default="7")
    target_city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    # Legacy column kept for backward-compatible migrations/data.
    purchased_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    payment_provider: Mapped[str | None] = mapped_column(String(60), nullable=True)
    payment_intent_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user = relationship("User", back_populates="promotions")
    listing = relationship("Listing", back_populates="promotions")
    payment = relationship("Payment", back_populates="promotion")


Index("ix_promotions_listing_status", Promotion.listing_id, Promotion.status)
Index("ix_promotions_user_status", Promotion.user_id, Promotion.status)
Index("ix_promotions_ends_at_status", Promotion.ends_at, Promotion.status)

