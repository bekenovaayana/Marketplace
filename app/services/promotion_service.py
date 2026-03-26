from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.payment import PaymentStatus
from app.models.promotion import Promotion, PromotionStatus, PromotionType
from app.models.user import User
from app.repositories.listing_repository import ListingRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.promotion_repository import PromotionRepository


class PromotionService:
    def __init__(self, db: Session):
        self.db = db
        self.promotions = PromotionRepository(db)
        self.payments = PaymentRepository(db)
        self.listings = ListingRepository(db)

    def create_promotion_after_payment_success(
        self,
        *,
        actor: User,
        payment_id: int,
        duration_days: int = 7,
        target_city: str | None = None,
        promotion_type: PromotionType = PromotionType.BOOSTED,
    ) -> Promotion:
        payment = self.payments.get_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if payment.user_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        if payment.status != PaymentStatus.SUCCESSFUL:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment must be successful first")

        listing = self.listings.get_by_id(payment.listing_id)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if listing.owner_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

        starts_at = datetime.now(timezone.utc)
        ends_at = starts_at + timedelta(days=max(1, duration_days))

        promo = Promotion(
            user_id=actor.id,
            listing_id=listing.id,
            payment_id=payment.id,
            promotion_type=promotion_type,
            status=PromotionStatus.ACTIVE,
            target_city=target_city,
            starts_at=starts_at,
            ends_at=ends_at,
            purchased_price=Decimal(payment.amount),
            currency=payment.currency,
        )

        try:
            self.promotions.create(promo)
            self.listings.update(listing, {"is_boosted": True})
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return promo

    def list_promotions(self, *, actor: User, page: int = 1, page_size: int = 20) -> tuple[list[Promotion], int]:
        return self.promotions.list(page=page, page_size=page_size, user_id=actor.id)

