from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.promotion import PromotionStatus
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.promotion import (
    PromotionCheckoutRequest,
    PromotionCheckoutResponse,
    PromotionOptionsResponse,
    PromotionRead,
)
from app.services.promotion_service import PromotionService


router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.get("/options", response_model=PromotionOptionsResponse)
def promotion_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromotionOptionsResponse:
    _ = current_user
    return PromotionOptionsResponse(**PromotionService(db).get_options())


@router.post("/checkout", response_model=PromotionCheckoutResponse, status_code=status.HTTP_201_CREATED)
def promotion_checkout(
    payload: PromotionCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromotionCheckoutResponse:
    _, provider_payload = PromotionService(db).checkout(actor=current_user, listing_id=payload.listing_id, days=payload.days)
    return PromotionCheckoutResponse(**provider_payload)


@router.get("", response_model=Page[PromotionRead])
def list_promotions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: PromotionStatus | None = Query(default=None, description="e.g. pending_payment for unpaid boosts"),
) -> Page[PromotionRead]:
    items, total = PromotionService(db).list_promotions(
        actor=current_user, page=page, page_size=page_size, status=status
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))


@router.get("/me", response_model=Page[PromotionRead], include_in_schema=False)
def list_my_promotions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[PromotionRead]:
    items, total = PromotionService(db).list_promotions(actor=current_user, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))
