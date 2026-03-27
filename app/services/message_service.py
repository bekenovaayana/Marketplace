from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.message_attachment import MessageAttachment
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.notification_service import NotificationService


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
        client_message_id: str | None = None,
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

        sanitized_attachments: list[dict] = []
        if attachments:
            if len(attachments) > 5:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="A message can include at most 5 attachments",
                )
            for attachment in attachments:
                file_url = str(attachment.get("file_url", "")).strip()
                if not file_url:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Attachment file_url is required",
                    )
                sanitized_attachments.append(
                    {
                        "file_name": attachment["file_name"],
                        "original_name": attachment.get("original_name"),
                        "mime_type": attachment["mime_type"],
                        "file_size": attachment["file_size"],
                        "file_url": file_url,
                    }
                )

        normalized_client_message_id = client_message_id.strip() if client_message_id else None
        if normalized_client_message_id:
            existing = self.messages.find_by_client_message_id(
                conversation_id=conversation_id,
                sender_id=actor.id,
                client_message_id=normalized_client_message_id,
            )
            if existing:
                return existing

        msg = Message(
            conversation_id=conversation_id,
            sender_id=actor.id,
            text_body=text_body.strip() if text_body else None,
            client_message_id=normalized_client_message_id,
        )

        if sanitized_attachments:
            msg.attachments = [
                MessageAttachment(
                    file_name=a["file_name"],
                    original_name=a.get("original_name"),
                    mime_type=a["mime_type"],
                    file_size=a["file_size"],
                    file_url=a["file_url"],
                )
                for a in sanitized_attachments
            ]

        self.messages.create(msg)

        # Notify the other participant about the new message.
        recipient_id = (
            convo.participant_b_id if actor.id == convo.participant_a_id else convo.participant_a_id
        )
        sender_name = actor.full_name or "Someone"
        NotificationService(self.db).notify_new_message(
            recipient_id=recipient_id,
            sender_name=sender_name,
            conversation_id=conversation_id,
        )
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

    def mark_read(self, *, actor: User, conversation_id: int) -> int:
        convo = self.conversations.get_by_id(conversation_id)
        if not convo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if actor.id not in (convo.participant_a_id, convo.participant_b_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        updated_count = self.messages.mark_read_for_conversation(conversation_id=conversation_id, actor_id=actor.id)
        self.db.commit()
        return updated_count

    def unread_summary(self, *, actor: User) -> dict:
        pairs = self.messages.unread_summary_by_conversation(actor_id=actor.id)
        by_conversation = [{"conversation_id": cid, "unread_count": count} for cid, count in pairs]
        total_unread = sum(count for _, count in pairs)
        return {"total_unread": total_unread, "by_conversation": by_conversation}

