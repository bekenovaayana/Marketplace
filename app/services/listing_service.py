from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.listing import Listing, ListingStatus
from app.models.user import User
from app.repositories.listing_repository import ListingRepository


class ListingService:
    def __init__(self, db: Session):
        self.db = db
        self.listings = ListingRepository(db)

    def create_listing(
        self,
        *,
        owner: User,
        category_id: int,
        title: str,
        description: str,
        price: Decimal,
        currency: str,
        city: str,
    ) -> Listing:
        listing = Listing(
            owner_id=owner.id,
            category_id=category_id,
            title=title,
            description=description,
            price=price,
            currency=currency,
            city=city,
            status=ListingStatus.ACTIVE,
        )
        self.listings.create(listing)
        self.db.commit()
        return listing

    def get_listing(self, *, listing_id: int, with_owner: bool = True) -> Listing:
        listing = self.listings.get_by_id(listing_id, with_owner=with_owner)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        return listing

    def get_public_listing(self, *, listing_id: int, with_owner: bool = True) -> Listing:
        listing = self.listings.get_by_id(listing_id, with_owner=with_owner)
        if not listing or listing.deleted_at is not None or listing.status != ListingStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        return listing

    def list_public_active(self, *, page: int = 1, page_size: int = 20, with_owner: bool = True) -> tuple[list[Listing], int]:
        return self.listings.list_public_active(page=page, page_size=page_size, with_owner=with_owner)

    def update_listing(self, *, listing_id: int, actor: User, data: dict) -> Listing:
        listing = self.listings.get_by_id(listing_id)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if listing.owner_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

        updated = self.listings.update(listing, data)
        self.db.commit()
        return updated

    def soft_delete_listing(self, *, listing_id: int, actor: User) -> Listing:
        listing = self.listings.get_by_id(listing_id)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if listing.owner_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

        updated = self.listings.update(
            listing,
            {"deleted_at": datetime.now(timezone.utc), "status": ListingStatus.INACTIVE},
        )
        self.db.commit()
        return updated

