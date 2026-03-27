from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="messages_sent")
    attachments = relationship("MessageAttachment", back_populates="message", cascade="all, delete-orphan")


Index("ix_messages_conversation_sent_at", Message.conversation_id, Message.sent_at)
Index("ix_messages_conversation_read_sender", Message.conversation_id, Message.is_read, Message.sender_id)
Index("ix_messages_client_message_id", Message.client_message_id)

