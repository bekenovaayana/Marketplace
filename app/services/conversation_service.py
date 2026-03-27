from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.user_repository import UserRepository


class ConversationService:
    def __init__(self, db: Session):
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.users = UserRepository(db)

    def create_or_get_conversation(
        self,
        *,
        actor: User,
        participant_id: int,
        listing_id: int | None = None,
    ) -> Conversation:
        if participant_id == actor.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot message yourself")

        other = self.users.get_by_id(participant_id)
        if not other:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        existing = self.conversations.get_between_users(
            user_a_id=actor.id,
            user_b_id=participant_id,
            listing_id=listing_id,
        )
        if existing:
            return existing

        convo = Conversation(
            participant_a_id=actor.id,
            participant_b_id=participant_id,
            listing_id=listing_id,
        )
        self.conversations.create(convo)
        self.db.commit()
        return convo

    def list_conversations(
        self,
        *,
        actor: User,
        page: int = 1,
        page_size: int = 20,
        with_participants: bool = True,
    ) -> tuple[list[Conversation], int]:
        items, total = self.conversations.list(page=page, page_size=page_size, user_id=actor.id, with_participants=with_participants)
        conversation_ids = [conversation.id for conversation in items]
        last_messages = self.messages.get_last_message_by_conversation_ids(conversation_ids=conversation_ids)
        unread_pairs = self.messages.unread_summary_by_conversation(actor_id=actor.id)
        unread_map = {conversation_id: unread for conversation_id, unread in unread_pairs}

        for conversation in items:
            last_message = last_messages.get(conversation.id)
            if last_message is not None:
                setattr(conversation, "last_message_text", last_message.text_body)
                setattr(conversation, "last_message_at", last_message.sent_at)
            else:
                setattr(conversation, "last_message_text", None)
                setattr(conversation, "last_message_at", None)
            setattr(conversation, "unread_count", unread_map.get(conversation.id, 0))

            listing = conversation.listing
            if listing is not None:
                setattr(conversation, "listing_title", listing.title)
                setattr(conversation, "listing_price", float(listing.price) if listing.price is not None else None)
                first_image = listing.images[0].url if listing.images else None
                setattr(conversation, "listing_image_url", first_image)
            else:
                setattr(conversation, "listing_title", None)
                setattr(conversation, "listing_price", None)
                setattr(conversation, "listing_image_url", None)

        return items, total

