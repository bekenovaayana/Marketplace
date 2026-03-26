from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    preferred_language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            name="user_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        server_default=UserStatus.ACTIVE.value,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    listings = relationship("Listing", back_populates="owner")
    favorites = relationship("Favorite", back_populates="user")
    conversations_a = relationship("Conversation", back_populates="participant_a", foreign_keys="Conversation.participant_a_id")
    conversations_b = relationship("Conversation", back_populates="participant_b", foreign_keys="Conversation.participant_b_id")
    messages_sent = relationship("Message", back_populates="sender")
    payments = relationship("Payment", back_populates="user")
    promotions = relationship("Promotion", back_populates="user")


Index("ix_users_status", User.status)

