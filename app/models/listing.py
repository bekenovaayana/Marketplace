from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.category import Category
from app.models.mixins import TimestampMixin
from app.models.user import User


class ListingStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SOLD = "sold"


class Listing(Base, TimestampMixin):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True)

    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    status: Mapped[ListingStatus] = mapped_column(
        Enum(
            ListingStatus,
            name="listing_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        server_default=ListingStatus.DRAFT.value,
        index=True,
    )
    is_boosted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0", index=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    owner = relationship(User, back_populates="listings")
    category = relationship(Category, back_populates="listings")
    images = relationship(
        "ListingImage",
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="(ListingImage.sort_order, ListingImage.id)",
    )
    favorites = relationship("Favorite", back_populates="listing")
    conversations = relationship("Conversation", back_populates="listing")
    payments = relationship("Payment", back_populates="listing")
    promotions = relationship("Promotion", back_populates="listing")


Index("ix_listings_public_feed", Listing.status, Listing.deleted_at, Listing.is_boosted, Listing.created_at)
Index("ix_listings_price", Listing.price)

