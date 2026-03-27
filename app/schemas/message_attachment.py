from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampFields


class MessageAttachmentCreate(BaseSchema):
    file_name: str = Field(min_length=1, max_length=255, examples=["9f4bb7f3ca6f43c49643c6de63a4bcf2.pdf"])
    original_name: str | None = Field(default=None, max_length=255, examples=["invoice-march.pdf"])
    mime_type: str = Field(min_length=1, max_length=120, examples=["application/pdf"])
    file_size: int = Field(ge=1, examples=[245811])
    file_url: str = Field(
        min_length=1,
        max_length=500,
        description="URL obtained from POST /attachments upload endpoint.",
        examples=["/uploads/messages/attachments/9f4bb7f3ca6f43c49643c6de63a4bcf2.pdf"],
    )


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


class MessageAttachmentUploadRead(BaseSchema):
    url: str = Field(
        description="Static file URL. Use this as attachments[].file_url in POST /messages.",
        examples=["/uploads/messages/attachments/9f4bb7f3ca6f43c49643c6de63a4bcf2.pdf"],
    )
    original_name: str = Field(
        description="Original filename received from client upload.",
        examples=["invoice-march.pdf"],
    )
    content_type: str = Field(
        description="Detected content type of uploaded file.",
        examples=["application/pdf"],
    )
    size_bytes: int = Field(
        ge=1,
        description="Uploaded file size in bytes.",
        examples=[245811],
    )

