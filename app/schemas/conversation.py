from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, Field

from app.schemas.common import BaseSchema, TimestampFields
from app.schemas.listing import ListingRead
from app.schemas.user import UserPublicRead


class ConversationCreate(BaseSchema):
    participant_id: int = Field(
        gt=0,
        validation_alias=AliasChoices("participant_id", "recipient_id", "other_user_id"),
        description="The other user id (aliases: recipient_id, other_user_id)",
    )
    listing_id: int | None = Field(default=None, gt=0, description="Optional listing context")


class ConversationUpdate(BaseSchema):
    pass


class ConversationRead(BaseSchema, TimestampFields):
    id: int
    listing_id: int | None
    participant_a_id: int
    participant_b_id: int


class ConversationWithParticipantsRead(ConversationRead):
    participant_a: UserPublicRead
    participant_b: UserPublicRead
    listing: ListingRead | None = None
    last_message_text: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0
    listing_title: str | None = None
    listing_price: float | None = None
    listing_image_url: str | None = None


class UnreadByConversationRead(BaseSchema):
    conversation_id: int
    unread_count: int


class UnreadSummaryRead(BaseSchema):
    total_unread: int
    by_conversation: list[UnreadByConversationRead]

