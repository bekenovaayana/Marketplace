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
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    preferred_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_verified: Mapped[bool] = mapped_column(default=False, nullable=False, server_default="0")
    phone_verified: Mapped[bool] = mapped_column(default=False, nullable=False, server_default="0")
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False, server_default="0")

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
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    reports_submitted = relationship("Report", foreign_keys="Report.reporter_user_id", back_populates="reporter")
    reports_reviewed = relationship("Report", foreign_keys="Report.reviewed_by_admin_id", back_populates="reviewed_by_admin")

    @property
    def profile_completed(self) -> bool:
        required = [self.full_name, self.phone, self.city, self.bio, self.avatar_url]
        return all(bool(v and str(v).strip()) for v in required)

    @property
    def trust_score(self) -> int:
        score = 0
        if self.phone_verified:
            score += 30
        if self.email_verified:
            score += 20
        if self.avatar_url:
            score += 20
        if self.bio:
            score += 10
        if self.city:
            score += 10
        has_active_listing = any(getattr(getattr(listing, "status", None), "value", None) == "active" for listing in (self.listings or []))
        if has_active_listing:
            score += 10
        return max(0, min(100, score))


Index("ix_users_status", User.status)

