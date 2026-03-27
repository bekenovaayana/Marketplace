from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = NotificationRepository(db)

    # ------------------------------------------------------------------ #
    # Public factory helpers — called by other services                   #
    # ------------------------------------------------------------------ #

    def notify_new_message(
        self,
        *,
        recipient_id: int,
        sender_name: str,
        conversation_id: int,
    ) -> Notification | None:
        recipient = self.db.get(User, recipient_id)
        if not recipient or not recipient.notify_new_message:
            return None
        n = self.repo.create_notification(
            user_id=recipient_id,
            notification_type=NotificationType.NEW_MESSAGE,
            title="New message",
            body=f"{sender_name} sent you a message",
            entity_type="conversation",
            entity_id=conversation_id,
        )
        self.db.commit()
        return n

    def notify_listing_favorited(
        self,
        *,
        owner_id: int,
        favoriter_id: int,
        listing_id: int,
        listing_title: str,
        favoriter_name: str,
    ) -> Notification | None:
        if owner_id == favoriter_id:
            return None
        owner = self.db.get(User, owner_id)
        if not owner or not owner.notify_listing_favorited:
            return None
        safe_title = listing_title.strip() if listing_title else "Listing"
        n = self.repo.create_notification(
            user_id=owner_id,
            notification_type=NotificationType.LISTING_FAVORITED,
            title="Listing favorited",
            body=f'{favoriter_name} added "{safe_title}" to favorites',
            entity_type="listing",
            entity_id=listing_id,
        )
        self.db.commit()
        return n

    def notify_contact_request(
        self,
        *,
        owner_id: int,
        requester_id: int,
        listing_id: int,
        listing_title: str,
        requester_name: str,
    ) -> Notification | None:
        if owner_id == requester_id:
            return None
        owner = self.db.get(User, owner_id)
        if not owner or not owner.notify_contact_request:
            return None
        safe_title = listing_title.strip() if listing_title else "Listing"
        n = self.repo.create_notification(
            user_id=owner_id,
            notification_type=NotificationType.CONTACT_REQUEST,
            title="Contact request",
            body=f'{requester_name} wants to contact you about "{safe_title}"',
            entity_type="listing",
            entity_id=listing_id,
        )
        self.db.commit()
        return n

    def notify_listing_approved(self, *, owner_id: int, listing_id: int, listing_title: str) -> Notification:
        n = self.repo.create_notification(
            user_id=owner_id,
            notification_type=NotificationType.LISTING_APPROVED,
            title="Listing approved",
            body=f'Your listing "{listing_title}" has been approved and is now public.',
            entity_type="listing",
            entity_id=listing_id,
        )
        self.db.commit()
        return n

    def notify_listing_rejected(
        self, *, owner_id: int, listing_id: int, listing_title: str, reason: str | None = None
    ) -> Notification:
        body = f'Your listing "{listing_title}" was rejected.'
        if reason:
            body += f" Reason: {reason}"
        n = self.repo.create_notification(
            user_id=owner_id,
            notification_type=NotificationType.LISTING_REJECTED,
            title="Listing rejected",
            body=body,
            entity_type="listing",
            entity_id=listing_id,
        )
        self.db.commit()
        return n

    def notify_payment_successful(self, *, user_id: int, payment_id: int, amount: str) -> Notification:
        n = self.repo.create_notification(
            user_id=user_id,
            notification_type=NotificationType.PAYMENT_SUCCESSFUL,
            title="Payment successful",
            body=f"Payment of {amount} was processed successfully.",
            entity_type="payment",
            entity_id=payment_id,
        )
        self.db.commit()
        return n

    def notify_promotion_activated(self, *, user_id: int, promotion_id: int, listing_title: str) -> Notification:
        n = self.repo.create_notification(
            user_id=user_id,
            notification_type=NotificationType.PROMOTION_ACTIVATED,
            title="Promotion activated",
            body=f'Your promotion for "{listing_title}" is now active.',
            entity_type="promotion",
            entity_id=promotion_id,
        )
        self.db.commit()
        return n

    def notify_promotion_expired(self, *, user_id: int, promotion_id: int, listing_title: str) -> Notification:
        n = self.repo.create_notification(
            user_id=user_id,
            notification_type=NotificationType.PROMOTION_EXPIRED,
            title="Promotion expired",
            body=f'Your promotion for "{listing_title}" has expired.',
            entity_type="promotion",
            entity_id=promotion_id,
        )
        self.db.commit()
        return n

    # ------------------------------------------------------------------ #
    # User-facing read operations                                         #
    # ------------------------------------------------------------------ #

    def list_notifications(
        self,
        *,
        actor: User,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        return self.repo.list_for_user(
            user_id=actor.id, page=page, page_size=page_size, unread_only=unread_only
        )

    def unread_count(self, *, actor: User) -> int:
        return self.repo.unread_count(user_id=actor.id)

    def mark_read(self, *, actor: User, notification_id: int) -> int:
        n = self.repo.get_by_id(notification_id, user_id=actor.id)
        if not n:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        updated = self.repo.mark_read(notification_id=notification_id, user_id=actor.id)
        self.db.commit()
        return updated

    def mark_all_read(self, *, actor: User) -> int:
        updated = self.repo.mark_all_read(user_id=actor.id)
        self.db.commit()
        return updated
