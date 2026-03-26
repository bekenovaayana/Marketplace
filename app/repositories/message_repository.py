from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

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

    def update(self, message: Message, data: dict) -> Message:
        for k, v in data.items():
            setattr(message, k, v)
        self.db.flush()
        self.db.refresh(message)
        return message

    def delete(self, message: Message) -> None:
        self.db.delete(message)
        self.db.flush()

