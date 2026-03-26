from __future__ import annotations

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"), nullable=True, index=True)

    participant_a_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    participant_b_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    listing = relationship("Listing", back_populates="conversations")
    participant_a = relationship("User", back_populates="conversations_a", foreign_keys=[participant_a_id])
    participant_b = relationship("User", back_populates="conversations_b", foreign_keys=[participant_b_id])

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


Index("ix_conversations_participants", Conversation.participant_a_id, Conversation.participant_b_id, Conversation.listing_id)

