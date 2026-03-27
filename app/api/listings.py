from __future__ import annotations

from decimal import Decimal
from enum import Enum

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_optional_current_user
from app.db.session import get_db
from app.models.listing import ListingStatus
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.listing import (
    ListingCreate,
    ListingDraftCreate,
    ListingImageReorderRequest,
    ListingMyStatus,
    ListingPublicRead,
    ListingUpdate,
    ListingWithOwnerRead,
    PublishListingResponse,
)
from app.schemas.user import DetailMessage
from app.services.listing_service import ListingService


router = APIRouter(prefix="/listings", tags=["listings"])


class ListingSort(str, Enum):
    NEWEST = "newest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    RECOMMENDED = "recommended"
    RELEVANCE = "relevance"


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
    current_user: User | None = Depends(get_optional_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(default=None, description="Search keyword for title/description", example="acer"),
    category_id: int | None = Query(default=None, gt=0, description="Filter by category id", example=1),
    city: str | None = Query(default=None, description="Filter by city (exact or startswith)", example="Bishkek"),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    sort: ListingSort = Query(
        default=ListingSort.NEWEST,
        description="Sort mode: newest, price_asc, price_desc, recommended, relevance",
        example="relevance",
    ),
    include_facets: bool = Query(default=False, description="Include optional facets metadata", example=True),
) -> Page[ListingPublicRead]:
    items, total, facets = ListingService(db).list_public_active(
        page=page,
        page_size=page_size,
        q=q,
        category_id=category_id,
        city=city,
        min_price=min_price,
        max_price=max_price,
        sort=sort.value,
        actor=current_user,
        include_facets=include_facets,
        with_owner=True,
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(
        items=items,
        meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages),
        facets=facets,
    )


class MyListingsSort(str, Enum):
    NEWEST = "newest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"


@router.get("/me", response_model=Page[ListingWithOwnerRead])
def list_my_listings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: ListingMyStatus | None = Query(default=None, alias="status"),
    category_id: int | None = Query(default=None, gt=0, description="Filter by listing category"),
    sort: MyListingsSort = Query(
        default=MyListingsSort.NEWEST,
        description="Sort: newest, price_asc, price_desc; boosted listings rank first",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ListingWithOwnerRead]:
    filter_value = ListingStatus(status_filter.value) if status_filter else None
    items, total = ListingService(db).list_my_listings(
        actor=current_user,
        status_filter=filter_value,
        category_id=category_id,
        sort=sort.value,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))


@router.post("/drafts", response_model=ListingWithOwnerRead, status_code=status.HTTP_201_CREATED)
def create_draft_listing(
    payload: ListingDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListingWithOwnerRead:
    listing = ListingService(db).create_draft_listing(owner=current_user, **payload.model_dump())
    return ListingService(db).get_listing(listing_id=listing.id, with_owner=True)


@router.put("/drafts/{listing_id}", response_model=ListingWithOwnerRead)
def update_draft_listing(
    listing_id: int,
    payload: ListingDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListingWithOwnerRead:
    updated = ListingService(db).update_draft_listing(
        listing_id=listing_id,
        actor=current_user,
        data=payload.model_dump(exclude_unset=True),
    )
    return ListingService(db).get_listing(listing_id=updated.id, with_owner=True)


@router.put("/{listing_id}/images/reorder", response_model=ListingWithOwnerRead)
def reorder_listing_images(
    listing_id: int,
    payload: ListingImageReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ListingWithOwnerRead:
    updated = ListingService(db).reorder_images(listing_id=listing_id, actor=current_user, images=[i.model_dump() for i in payload.images])
    return ListingService(db).get_listing(listing_id=updated.id, with_owner=True)


@router.post("/{listing_id}/publish", response_model=PublishListingResponse)
def publish_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PublishListingResponse:
    listing = ListingService(db).publish_listing(listing_id=listing_id, actor=current_user)
    reloaded = ListingService(db).get_listing(listing_id=listing.id, with_owner=True)
    return PublishListingResponse(detail="Listing published successfully", listing=reloaded)


@router.post("/{listing_id}/unpublish", response_model=PublishListingResponse)
def unpublish_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PublishListingResponse:
    listing = ListingService(db).unpublish_listing(listing_id=listing_id, actor=current_user)
    reloaded = ListingService(db).get_listing(listing_id=listing.id, with_owner=True)
    return PublishListingResponse(detail="Listing unpublished successfully", listing=reloaded)


@router.get("/{listing_id}/preview", response_model=ListingWithOwnerRead)
def preview_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> ListingWithOwnerRead:
    return ListingService(db).get_preview_listing(listing_id=listing_id, actor=current_user, with_owner=True)


@router.post(
    "/{listing_id}/contact-intent",
    response_model=DetailMessage,
    status_code=status.HTTP_201_CREATED,
    summary="Notify seller of contact interest",
    description=(
        "Records that the current user wants to contact the seller about this listing. "
        "Throttled to once per listing per 24 hours. Does not replace chat messages "
        "(see notify_new_message); uses notify_contact_request preference on the seller."
    ),
)
def record_listing_contact_intent(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DetailMessage:
    ListingService(db).record_contact_intent(actor=current_user, listing_id=listing_id)
    return DetailMessage(detail="Contact request recorded")


@router.get("/{listing_id}", response_model=ListingPublicRead)
def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> ListingPublicRead:
    return ListingService(db).get_public_listing(listing_id=listing_id, actor=current_user, with_owner=True)


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

