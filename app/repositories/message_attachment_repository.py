from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.message import Message
from app.models.message_attachment import MessageAttachment
from app.repositories.base import BaseRepository


class MessageAttachmentRepository(BaseRepository[MessageAttachment]):
    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_id(self, attachment_id: int, *, with_message: bool = False) -> MessageAttachment | None:
        if not with_message:
            return self.db.get(MessageAttachment, attachment_id)
        stmt = (
            select(MessageAttachment)
            .where(MessageAttachment.id == attachment_id)
            .options(joinedload(MessageAttachment.message).joinedload(Message.conversation))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_message_id(self, message_id: int) -> list[MessageAttachment]:
        stmt = (
            select(MessageAttachment)
            .where(MessageAttachment.message_id == message_id)
            .order_by(MessageAttachment.id.asc())
        )
        return self.db.execute(stmt).scalars().all()
