from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class NotificationType(str, enum.Enum):
    NEW_MESSAGE = "new_message"
    LISTING_APPROVED = "listing_approved"
    LISTING_REJECTED = "listing_rejected"
    REPORT_STATUS_CHANGED = "report_status_changed"
    PAYMENT_SUCCESSFUL = "payment_successful"
    PROMOTION_ACTIVATED = "promotion_activated"
    PROMOTION_EXPIRED = "promotion_expired"
    LISTING_FAVORITED = "listing_favorited"
    CONTACT_REQUEST = "contact_request"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="notifications")


Index("ix_notifications_user_is_read", Notification.user_id, Notification.is_read)
Index("ix_notifications_user_created_at", Notification.user_id, Notification.created_at)
