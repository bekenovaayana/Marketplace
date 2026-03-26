from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampFields
from app.schemas.listing import ListingRead
from app.schemas.user import UserPublicRead


class ConversationCreate(BaseSchema):
    participant_id: int = Field(gt=0, description="The other user")
    listing_id: int | None = Field(default=None, gt=0)


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

