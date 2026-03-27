from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentWebhookRequest
from app.services.payment_service import PaymentService
from app.services.promotion_service import PromotionService


router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRead:
    return PaymentService(db).create_payment(
        actor=current_user,
        listing_id=payload.listing_id,
        amount=payload.amount,
        currency=payload.currency,
    )


@router.post("/{payment_id}/simulate-success", response_model=PaymentRead)
def simulate_success(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentRead:
    return PaymentService(db).simulate_success(actor=current_user, payment_id=payment_id)


@router.post("/webhook", response_model=PaymentRead, summary="Mock payment provider webhook")
def webhook(
    payload: PaymentWebhookRequest,
    db: Session = Depends(get_db),
) -> PaymentRead:
    payment = PaymentService(db).process_webhook(provider_reference=payload.provider_reference, event=payload.event)
    # If this payment is linked to a promotion, finalize it too.
    try:
        PromotionService(db).finalize_from_payment(payment_intent_id=payload.provider_reference, event=payload.event)
    except Exception:
        # If no promotion exists, ignore (payments can exist independently).
        pass
    return payment


@router.get("", response_model=Page[PaymentRead])
def list_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[PaymentRead]:
    items, total = PaymentService(db).list_payments(actor=current_user, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))

