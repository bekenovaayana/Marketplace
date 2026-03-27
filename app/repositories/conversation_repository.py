from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.conversation import Conversation
from app.models.listing import Listing
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        self.db.flush()
        self.db.refresh(conversation)
        return conversation

    def get_by_id(self, conversation_id: int, *, with_participants: bool = False) -> Conversation | None:
        if not with_participants:
            return self.db.get(Conversation, conversation_id)
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                joinedload(Conversation.participant_a),
                joinedload(Conversation.participant_b),
                selectinload(Conversation.listing).selectinload(Listing.images),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_between_users(
        self,
        *,
        user_a_id: int,
        user_b_id: int,
        listing_id: int | None = None,
    ) -> Conversation | None:
        participants_clause = or_(
            and_(Conversation.participant_a_id == user_a_id, Conversation.participant_b_id == user_b_id),
            and_(Conversation.participant_a_id == user_b_id, Conversation.participant_b_id == user_a_id),
        )
        stmt = select(Conversation).where(participants_clause)
        if listing_id is not None:
            stmt = stmt.where(Conversation.listing_id == listing_id)
        return self.db.execute(stmt.order_by(Conversation.id.desc())).scalar_one_or_none()

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        user_id: int | None = None,
        with_participants: bool = False,
    ) -> tuple[list[Conversation], int]:
        stmt = select(Conversation).order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        if user_id is not None:
            stmt = stmt.where(or_(Conversation.participant_a_id == user_id, Conversation.participant_b_id == user_id))
        if with_participants:
            stmt = stmt.options(
                joinedload(Conversation.participant_a),
                joinedload(Conversation.participant_b),
                selectinload(Conversation.listing).selectinload(Listing.images),
            )
        return self._paginate(stmt, page=page, page_size=page_size)

    def update(self, conversation: Conversation, data: dict) -> Conversation:
        for k, v in data.items():
            setattr(conversation, k, v)
        self.db.flush()
        self.db.refresh(conversation)
        return conversation

    def delete(self, conversation: Conversation) -> None:
        self.db.delete(conversation)
        self.db.flush()

