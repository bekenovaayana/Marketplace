from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.repositories.listing_repository import ListingRepository
from app.repositories.payment_repository import PaymentRepository


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.payments = PaymentRepository(db)
        self.listings = ListingRepository(db)

    def create_payment(self, *, actor: User, listing_id: int, amount: Decimal, currency: str = "USD") -> Payment:
        listing = self.listings.get_by_id(listing_id)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        payment = Payment(
            user_id=actor.id,
            listing_id=listing_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PENDING,
            provider="mock",
        )
        self.payments.create(payment)
        self.db.commit()
        return payment

    def simulate_success(self, *, actor: User, payment_id: int) -> Payment:
        payment = self.payments.get_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if payment.user_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        if payment.status != PaymentStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment is not pending")

        updated = self.payments.update(
            payment,
            {
                "status": PaymentStatus.SUCCESSFUL,
                "paid_at": datetime.now(timezone.utc),
                "provider_reference": f"mock_{uuid4().hex}",
            },
        )
        self.db.commit()
        return updated

    def list_payments(self, *, actor: User, page: int = 1, page_size: int = 20) -> tuple[list[Payment], int]:
        return self.payments.list(page=page, page_size=page_size, user_id=actor.id)

