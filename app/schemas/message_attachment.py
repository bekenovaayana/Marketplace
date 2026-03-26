from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampFields


class MessageAttachmentCreate(BaseSchema):
    file_name: str = Field(min_length=1, max_length=255)
    original_name: str | None = Field(default=None, max_length=255)
    mime_type: str = Field(min_length=1, max_length=120)
    file_size: int = Field(ge=1)
    file_url: str = Field(min_length=1, max_length=500)


class MessageAttachmentUpdate(BaseSchema):
    pass


class MessageAttachmentRead(BaseSchema, TimestampFields):
    id: int
    message_id: int
    file_name: str
    original_name: str | None
    mime_type: str
    file_size: int
    file_url: str

