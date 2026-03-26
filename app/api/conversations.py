from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.conversation import ConversationCreate, ConversationWithParticipantsRead
from app.services.conversation_service import ConversationService


router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationWithParticipantsRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationWithParticipantsRead:
    convo = ConversationService(db).create_or_get_conversation(
        actor=current_user,
        participant_id=payload.participant_id,
        listing_id=payload.listing_id,
    )
    convo = ConversationService(db).conversations.get_by_id(convo.id, with_participants=True)
    return convo


@router.get("", response_model=Page[ConversationWithParticipantsRead])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ConversationWithParticipantsRead]:
    items, total = ConversationService(db).list_conversations(actor=current_user, page=page, page_size=page_size, with_participants=True)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))

