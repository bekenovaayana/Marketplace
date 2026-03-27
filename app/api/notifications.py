from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.notification import MarkReadResponse, NotificationRead, NotificationUnreadCountRead
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationRead])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False, description="Return only unread notifications"),
) -> Page[NotificationRead]:
    items, total = NotificationService(db).list_notifications(
        actor=current_user, page=page, page_size=page_size, unread_only=unread_only
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))


@router.get("/unread-count", response_model=NotificationUnreadCountRead)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationUnreadCountRead:
    count = NotificationService(db).unread_count(actor=current_user)
    return NotificationUnreadCountRead(unread_count=count)


@router.post("/{notification_id}/read", response_model=MarkReadResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkReadResponse:
    updated = NotificationService(db).mark_read(actor=current_user, notification_id=notification_id)
    detail = "Notification marked as read" if updated else "Notification was already read"
    return MarkReadResponse(detail=detail, updated_count=updated)


@router.post("/read-all", response_model=MarkReadResponse, status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarkReadResponse:
    updated = NotificationService(db).mark_all_read(actor=current_user)
    return MarkReadResponse(detail=f"Marked {updated} notification(s) as read", updated_count=updated)
