from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.conversation import UnreadSummaryRead
from app.services.message_service import MessageService

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("/unread-summary", response_model=UnreadSummaryRead)
def get_unread_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadSummaryRead:
    payload = MessageService(db).unread_summary(actor=current_user)
    return UnreadSummaryRead(**payload)
