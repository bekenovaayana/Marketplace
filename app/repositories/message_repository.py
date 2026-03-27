from __future__ import annotations

from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, message: Message) -> Message:
        self.db.add(message)
        self.db.flush()
        self.db.refresh(message)
        return message

    def get_by_id(self, message_id: int, *, with_sender: bool = False) -> Message | None:
        if not with_sender:
            return self.db.get(Message, message_id)
        stmt = (
            select(Message)
            .where(Message.id == message_id)
            .options(joinedload(Message.sender), selectinload(Message.attachments))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, *, page: int = 1, page_size: int = 50) -> tuple[list[Message], int]:
        stmt = select(Message).order_by(Message.sent_at.desc(), Message.id.desc())
        return self._paginate(stmt, page=page, page_size=page_size)

    def list_by_conversation_id(
        self,
        *,
        conversation_id: int,
        page: int = 1,
        page_size: int = 50,
        with_sender: bool = False,
    ) -> tuple[list[Message], int]:
        stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.sent_at.asc(), Message.id.asc())
        if with_sender:
            stmt = stmt.options(joinedload(Message.sender), selectinload(Message.attachments))
        return self._paginate(stmt, page=page, page_size=page_size)

    def find_by_client_message_id(
        self,
        *,
        conversation_id: int,
        sender_id: int,
        client_message_id: str,
    ) -> Message | None:
        stmt = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.sender_id == sender_id,
            Message.client_message_id == client_message_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def mark_read_for_conversation(self, *, conversation_id: int, actor_id: int) -> int:
        stmt = (
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != actor_id,
                Message.is_read.is_(False),
            )
            .values(is_read=True)
        )
        result = self.db.execute(stmt)
        return int(result.rowcount or 0)

    def unread_count_for_conversation(self, *, conversation_id: int, actor_id: int) -> int:
        stmt = select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id,
            Message.sender_id != actor_id,
            Message.is_read.is_(False),
        )
        return int(self.db.execute(stmt).scalar_one())

    def unread_summary_by_conversation(self, *, actor_id: int) -> list[tuple[int, int]]:
        stmt = (
            select(Message.conversation_id, func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                and_(
                    Message.sender_id != actor_id,
                    Message.is_read.is_(False),
                    ((Conversation.participant_a_id == actor_id) | (Conversation.participant_b_id == actor_id)),
                )
            )
            .group_by(Message.conversation_id)
        )
        return [(int(row[0]), int(row[1])) for row in self.db.execute(stmt).all()]

    def get_last_message_by_conversation_ids(self, *, conversation_ids: list[int]) -> dict[int, Message]:
        if not conversation_ids:
            return {}
        subquery = (
            select(Message.conversation_id, func.max(Message.sent_at).label("max_sent_at"))
            .where(Message.conversation_id.in_(conversation_ids))
            .group_by(Message.conversation_id)
            .subquery()
        )
        stmt = (
            select(Message)
            .join(
                subquery,
                and_(
                    Message.conversation_id == subquery.c.conversation_id,
                    Message.sent_at == subquery.c.max_sent_at,
                ),
            )
            .order_by(Message.id.desc())
        )
        messages = self.db.execute(stmt).scalars().all()
        result: dict[int, Message] = {}
        for message in messages:
            result.setdefault(message.conversation_id, message)
        return result

    def update(self, message: Message, data: dict) -> Message:
        for k, v in data.items():
            setattr(message, k, v)
        self.db.flush()
        self.db.refresh(message)
        return message

    def delete(self, message: Message) -> None:
        self.db.delete(message)
        self.db.flush()

