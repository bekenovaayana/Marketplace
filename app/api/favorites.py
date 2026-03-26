from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.favorite import FavoriteWithListingRead
from app.services.favorite_service import FavoriteService


router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("/{listing_id}", response_model=FavoriteWithListingRead, status_code=status.HTTP_201_CREATED)
def add_favorite(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoriteWithListingRead:
    fav = FavoriteService(db).add_favorite(actor=current_user, listing_id=listing_id)
    return FavoriteService(db).get_favorite(favorite_id=fav.id)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    FavoriteService(db).remove_favorite(actor=current_user, listing_id=listing_id)
    return None


@router.get("", response_model=Page[FavoriteWithListingRead])
def list_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[FavoriteWithListingRead]:
    items, total = FavoriteService(db).list_favorites(actor=current_user, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))

