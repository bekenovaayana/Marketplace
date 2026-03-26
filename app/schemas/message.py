from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampFields
from app.schemas.message_attachment import MessageAttachmentCreate, MessageAttachmentRead
from app.schemas.user import UserPublicRead


class MessageCreate(BaseSchema):
    conversation_id: int = Field(gt=0)
    text_body: str | None = Field(default=None, max_length=5000)
    attachments: list[MessageAttachmentCreate] = []


class MessageUpdate(BaseSchema):
    is_read: bool | None = None


class MessageRead(BaseSchema, TimestampFields):
    id: int
    conversation_id: int
    sender_id: int
    text_body: str | None
    is_read: bool
    sent_at: datetime


class MessageWithSenderRead(MessageRead):
    sender: UserPublicRead
    attachments: list[MessageAttachmentRead] = []

