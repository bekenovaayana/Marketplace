from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.notification import NotificationType
from app.schemas.common import BaseSchema, TimestampFields


class NotificationRead(BaseSchema, TimestampFields):
    id: int
    user_id: int
    notification_type: NotificationType
    title: str
    body: str | None
    entity_type: str | None
    entity_id: int | None
    is_read: bool
    read_at: datetime | None


class NotificationUnreadCountRead(BaseSchema):
    unread_count: int = Field(ge=0, description="Total unread notifications for current user")


class MarkReadResponse(BaseSchema):
    detail: str
    updated_count: int = Field(ge=0, description="Number of notifications marked as read")
