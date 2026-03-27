from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.message import MarkReadResponse, MessageCreate, MessageWithSenderRead
from app.services.message_service import MessageService


router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessageWithSenderRead, status_code=status.HTTP_201_CREATED)
def send_message(
    payload: MessageCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageWithSenderRead:
    msg = MessageService(db).send_message(
        actor=current_user,
        conversation_id=payload.conversation_id,
        text_body=payload.text_body,
        client_message_id=payload.client_message_id or idempotency_key,
        attachments=[a.model_dump() for a in payload.attachments] if payload.attachments else [],
    )
    msg = MessageService(db).messages.get_by_id(msg.id, with_sender=True)
    return msg


@router.get("/{conversation_id}", response_model=Page[MessageWithSenderRead])
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Page[MessageWithSenderRead]:
    items, total = MessageService(db).list_messages(
        actor=current_user,
        conversation_id=conversation_id,
        page=page,
        page_size=page_size,
        with_sender=True,
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))


@router.post("/{conversation_id}/mark-read", response_model=MarkReadResponse)
def mark_messages_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkReadResponse:
    updated_count = MessageService(db).mark_read(actor=current_user, conversation_id=conversation_id)
    return MarkReadResponse(detail="Messages marked as read", updated_count=updated_count)

