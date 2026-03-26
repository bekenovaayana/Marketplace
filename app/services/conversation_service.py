from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.user_repository import UserRepository


class ConversationService:
    def __init__(self, db: Session):
        self.db = db
        self.conversations = ConversationRepository(db)
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
        return self.conversations.list(page=page, page_size=page_size, user_id=actor.id, with_participants=with_participants)

