from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.promotion import PromotionActivateRequest, PromotionRead
from app.services.promotion_service import PromotionService


router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.post("", response_model=PromotionRead, status_code=status.HTTP_201_CREATED)
def create_promotion(
    payload: PromotionActivateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PromotionRead:
    return PromotionService(db).create_promotion_after_payment_success(
        actor=current_user,
        payment_id=payload.payment_id,
        duration_days=payload.duration_days,
        target_city=payload.target_city,
    )


@router.get("", response_model=Page[PromotionRead])
def list_promotions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[PromotionRead]:
    items, total = PromotionService(db).list_promotions(actor=current_user, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))

