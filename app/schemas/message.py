from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, Field, computed_field, model_validator

from app.schemas.common import BaseSchema, TimestampFields
from app.schemas.message_attachment import MessageAttachmentCreate, MessageAttachmentRead
from app.schemas.user import UserPublicRead


class MessageCreate(BaseSchema):
    conversation_id: int = Field(gt=0, description="Conversation id")
    text_body: str | None = Field(
        default=None,
        max_length=5000,
        validation_alias=AliasChoices("text_body", "content"),
        description="Message text (alias: content)",
    )
    attachments: list[MessageAttachmentCreate] = Field(
        default_factory=list,
        description=(
            "Optional attachments metadata. Flow: upload file with POST /attachments, "
            "then pass returned url as attachments[].file_url in this request."
        ),
    )
    client_message_id: str | None = Field(default=None, max_length=100, description="Optional idempotency key per message")

    @model_validator(mode="before")
    @classmethod
    def normalize_text_alias(cls, data: object) -> object:
        if isinstance(data, dict):
            if data.get("text_body") is None and data.get("content") is not None:
                data["text_body"] = data["content"]
        return data


class MessageUpdate(BaseSchema):
    is_read: bool | None = None


class MessageRead(BaseSchema, TimestampFields):
    id: int
    conversation_id: int
    sender_id: int
    text_body: str | None
    client_message_id: str | None
    is_read: bool
    sent_at: datetime

    @computed_field
    @property
    def content(self) -> str | None:
        # Backward-compatible response alias for older clients.
        return self.text_body


class MessageWithSenderRead(MessageRead):
    sender: UserPublicRead
    attachments: list[MessageAttachmentRead] = []


class MarkReadResponse(BaseSchema):
    detail: str
    updated_count: int = Field(ge=0)

