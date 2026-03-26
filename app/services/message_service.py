from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.message_attachment import MessageAttachment
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository


class MessageService:
    def __init__(self, db: Session):
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)

    def send_message(
        self,
        *,
        actor: User,
        conversation_id: int,
        text_body: str | None,
        attachments: list[dict] | None = None,
    ) -> Message:
        convo = self.conversations.get_by_id(conversation_id)
        if not convo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        if actor.id not in (convo.participant_a_id, convo.participant_b_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

        if convo.participant_a_id == convo.participant_b_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation")

        if (not text_body or not text_body.strip()) and not (attachments and len(attachments) > 0):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message must have text or attachments")

        msg = Message(conversation_id=conversation_id, sender_id=actor.id, text_body=text_body.strip() if text_body else None)

        if attachments:
            msg.attachments = [
                MessageAttachment(
                    file_name=a["file_name"],
                    original_name=a.get("original_name"),
                    mime_type=a["mime_type"],
                    file_size=a["file_size"],
                    file_url=a["file_url"],
                )
                for a in attachments
            ]

        self.messages.create(msg)
        self.db.commit()
        return msg

    def list_messages(
        self,
        *,
        actor: User,
        conversation_id: int,
        page: int = 1,
        page_size: int = 50,
        with_sender: bool = True,
    ) -> tuple[list[Message], int]:
        convo = self.conversations.get_by_id(conversation_id)
        if not convo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if actor.id not in (convo.participant_a_id, convo.participant_b_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

        return self.messages.list_by_conversation_id(
            conversation_id=conversation_id,
            page=page,
            page_size=page_size,
            with_sender=with_sender,
        )

