from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.listing import ListingCreate, ListingPublicRead, ListingUpdate, ListingWithOwnerRead
from app.services.listing_service import ListingService


router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("", response_model=ListingWithOwnerRead, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListingWithOwnerRead:
    listing = ListingService(db).create_listing(owner=current_user, **payload.model_dump())
    # reload with relations for response
    listing = ListingService(db).get_listing(listing_id=listing.id, with_owner=True)
    return listing


@router.get("", response_model=Page[ListingPublicRead])
def list_listings(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ListingPublicRead]:
    items, total = ListingService(db).list_public_active(page=page, page_size=page_size, with_owner=True)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))


@router.get("/{listing_id}", response_model=ListingPublicRead)
def get_listing(listing_id: int, db: Session = Depends(get_db)) -> ListingPublicRead:
    return ListingService(db).get_public_listing(listing_id=listing_id, with_owner=True)


@router.put("/{listing_id}", response_model=ListingWithOwnerRead)
def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListingWithOwnerRead:
    updated = ListingService(db).update_listing(
        listing_id=listing_id,
        actor=current_user,
        data=payload.model_dump(exclude_unset=True),
    )
    return ListingService(db).get_listing(listing_id=updated.id, with_owner=True)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    ListingService(db).soft_delete_listing(listing_id=listing_id, actor=current_user)
    return None

