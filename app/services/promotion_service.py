from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.payment import PaymentStatus
from app.models.promotion import Promotion, PromotionStatus, PromotionType
from app.models.listing import ListingStatus
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

    def get_options(self) -> dict:
        currency = "USD"
        price_per_day = Decimal("1.00")
        durations = [7, 30]
        return {
            "currency": currency,
            "price_per_day": price_per_day,
            "options": [{"days": d, "price": (price_per_day * Decimal(d)), "currency": currency} for d in durations],
        }

    def checkout(self, *, actor: User, listing_id: int, days: int) -> tuple[Promotion, dict]:
        listing = self.listings.get_by_id(listing_id)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if listing.owner_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        if listing.status != ListingStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Listing must be active to promote")

        opts = self.get_options()
        price_per_day: Decimal = opts["price_per_day"]
        currency: str = opts["currency"]
        safe_days = max(1, min(365, int(days)))
        amount = price_per_day * Decimal(safe_days)

        # create a pending payment intent (mock)
        from app.services.payment_service import PaymentService

        payment = PaymentService(self.db).create_payment(actor=actor, listing_id=listing.id, amount=amount, currency=currency)

        now = datetime.now(timezone.utc)
        promo = Promotion(
            user_id=actor.id,
            listing_id=listing.id,
            payment_id=payment.id,
            promotion_type=PromotionType.BOOSTED,
            status=PromotionStatus.PENDING_PAYMENT,
            days=safe_days,
            target_city=listing.city,
            starts_at=now,
            ends_at=now,
            purchased_price=Decimal(amount),
            amount=Decimal(amount),
            currency=currency,
            payment_provider=payment.provider,
            payment_intent_id=payment.provider_reference,
        )
        self.promotions.create(promo)
        self.db.commit()

        provider_payload = {
            "promotion_id": promo.id,
            "payment_provider": payment.provider,
            "payment_intent_id": payment.provider_reference or "",
            "amount": amount,
            "currency": currency,
            "checkout_url": None,
            "client_secret": payment.provider_reference,
        }
        return promo, provider_payload

    def finalize_from_payment(self, *, payment_intent_id: str, event: str) -> Promotion:
        payment = self.payments.get_by_provider_reference(provider_reference=payment_intent_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        promo = self.promotions.get_by_payment_id(payment_id=payment.id)
        if not promo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion not found")

        if event == "payment_succeeded":
            if payment.status != PaymentStatus.SUCCESSFUL:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment not successful")
            if promo.status == PromotionStatus.ACTIVE:
                return promo
            now = datetime.now(timezone.utc)
            ends = now + timedelta(days=max(1, int(promo.days)))
            self.promotions.update(
                promo,
                {"status": PromotionStatus.ACTIVE, "starts_at": now, "ends_at": ends},
            )
            listing = self.listings.get_by_id(promo.listing_id)
            if listing:
                self.listings.update(listing, {"is_boosted": True})
            self.db.commit()
            return promo

        if event == "payment_failed":
            self.promotions.update(promo, {"status": PromotionStatus.CANCELLED})
            self.db.commit()
            return promo

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported webhook event")

    def list_promotions(
        self,
        *,
        actor: User,
        page: int = 1,
        page_size: int = 20,
        status: PromotionStatus | None = None,
    ) -> tuple[list[Promotion], int]:
        return self.promotions.list(page=page, page_size=page_size, user_id=actor.id, status=status)

