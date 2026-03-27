from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def get_by_id(self, notification_id: int, user_id: int) -> Notification | None:
        return (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )

    def list_for_user(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        q = self.db.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            q = q.filter(Notification.is_read == False)  # noqa: E712
        total = q.count()
        items = (
            q.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def unread_count(self, user_id: int) -> int:
        result = (
            self.db.query(func.count(Notification.id))
            .filter(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .scalar()
        )
        return result or 0

    def mark_read(self, notification_id: int, user_id: int) -> int:
        now = datetime.now(timezone.utc)
        result = self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
            )
            .values(is_read=True, read_at=now)
        )
        return result.rowcount

    def mark_all_read(self, user_id: int) -> int:
        now = datetime.now(timezone.utc)
        result = self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .values(is_read=True, read_at=now)
        )
        return result.rowcount

    def create_notification(
        self,
        *,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        body: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> Notification:
        n = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return self.create(n)
