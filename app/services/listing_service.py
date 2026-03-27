from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.listing_contact_intent import ListingContactIntent
from app.models.listing_image import ListingImage
from app.models.listing import Listing, ListingStatus
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.repositories.favorite_repository import FavoriteRepository
from app.repositories.listing_repository import ListingRepository
from app.services.notification_service import NotificationService

CONTACT_INTENT_THROTTLE_HOURS = 24


class ListingService:
    def __init__(self, db: Session):
        self.db = db
        self.listings = ListingRepository(db)
        self.categories = CategoryRepository(db)
        self.favorites = FavoriteRepository(db)

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
        contact_phone: str,
        latitude: Decimal | None = None,
        longitude: Decimal | None = None,
        images: list[dict] | None = None,
    ) -> Listing:
        if not self.categories.get_by_id(category_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        listing = Listing(
            owner_id=owner.id,
            category_id=category_id,
            title=title,
            description=description,
            price=price,
            currency=currency,
            city=city,
            contact_phone=contact_phone,
            latitude=latitude,
            longitude=longitude,
            status=ListingStatus.ACTIVE,
        )
        if images:
            listing.images = self._build_images(images)
        self.listings.create(listing)
        self.db.commit()
        return listing

    def create_draft_listing(
        self,
        *,
        owner: User,
        category_id: int | None = None,
        title: str | None = None,
        description: str | None = None,
        price: Decimal | None = None,
        currency: str = "USD",
        city: str | None = None,
        contact_phone: str | None = None,
        latitude: Decimal | None = None,
        longitude: Decimal | None = None,
        images: list[dict] | None = None,
    ) -> Listing:
        if category_id is not None and not self.categories.get_by_id(category_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        listing = Listing(
            owner_id=owner.id,
            category_id=category_id,
            title=title,
            description=description,
            price=price,
            currency=currency,
            city=city,
            contact_phone=contact_phone,
            latitude=latitude,
            longitude=longitude,
            status=ListingStatus.DRAFT,
        )
        if images:
            listing.images = self._build_images(images)
        self.listings.create(listing)
        self.db.commit()
        return listing

    def get_listing(self, *, listing_id: int, with_owner: bool = True) -> Listing:
        listing = self.listings.get_by_id(listing_id, with_owner=with_owner)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        return listing

    def get_public_listing(self, *, listing_id: int, actor: User | None = None, with_owner: bool = True) -> Listing:
        listing = self.listings.get_by_id(listing_id, with_owner=with_owner)
        if not listing or listing.deleted_at is not None or listing.status != ListingStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if actor is None or actor.id != listing.owner_id:
            listing = self.listings.increment_view_count(listing=listing)
            self.db.commit()
        return listing

    def get_preview_listing(self, *, listing_id: int, actor: User | None = None, with_owner: bool = True) -> Listing:
        listing = self.listings.get_by_id(listing_id, with_owner=with_owner)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if actor and listing.owner_id == actor.id:
            return listing
        if listing.status != ListingStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        return listing

    def list_public_active(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
        category_id: int | None = None,
        city: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        sort: str = "newest",
        actor: User | None = None,
        include_facets: bool = False,
        with_owner: bool = True,
    ) -> tuple[list[Listing], int, dict | None]:
        normalized_q = q.strip() if q else None
        normalized_city = city.strip() if city else None
        if normalized_q == "":
            normalized_q = None
        if normalized_city == "":
            normalized_city = None
        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="min_price cannot be greater than max_price",
            )
        effective_sort = sort
        if effective_sort == "relevance" and not normalized_q:
            effective_sort = "newest"
        affinity_category_ids: list[int] = []
        if effective_sort == "recommended" and actor is not None:
            affinity_category_ids = self.favorites.top_category_ids_for_user(user_id=actor.id, limit=5)

        items, total = self.listings.list_public_active(
            page=page,
            page_size=page_size,
            q=normalized_q,
            category_id=category_id,
            city=normalized_city,
            min_price=min_price,
            max_price=max_price,
            sort=effective_sort,
            affinity_category_ids=affinity_category_ids,
            with_owner=with_owner,
        )
        facets = None
        if include_facets:
            facets = self.listings.get_public_facets(
                q=normalized_q,
                category_id=category_id,
                city=normalized_city,
                min_price=min_price,
                max_price=max_price,
            )
        return items, total, facets

    def update_listing(self, *, listing_id: int, actor: User, data: dict) -> Listing:
        listing = self.listings.get_by_id(listing_id)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if listing.owner_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

        images = data.pop("images", None)
        if "category_id" in data and data["category_id"] is not None and not self.categories.get_by_id(data["category_id"]):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        if images is not None:
            listing.images = self._build_images(images)

        updated = self.listings.update(listing, data)
        self.db.commit()
        return updated

    def update_draft_listing(self, *, listing_id: int, actor: User, data: dict) -> Listing:
        listing = self.listings.get_by_id(listing_id)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if listing.owner_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        if listing.status not in (ListingStatus.DRAFT, ListingStatus.INACTIVE):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Listing is not editable as draft")

        images = data.pop("images", None)
        if "category_id" in data and data["category_id"] is not None and not self.categories.get_by_id(data["category_id"]):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        if images is not None:
            listing.images = self._build_images(images)
        updated = self.listings.update(listing, data)
        self.db.commit()
        return updated

    def reorder_images(self, *, listing_id: int, actor: User, images: list[dict]) -> Listing:
        listing = self.listings.get_by_id(listing_id)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if listing.owner_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        listing.images = self._build_images(images)
        self.db.flush()
        self.db.commit()
        return listing

    def publish_listing(self, *, listing_id: int, actor: User) -> Listing:
        listing = self.listings.get_by_id(listing_id, with_owner=True)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if listing.owner_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        missing_fields = self._get_missing_publish_fields(listing)
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"message": "Draft is incomplete", "missing_fields": missing_fields},
            )
        listing.status = ListingStatus.ACTIVE
        self.db.flush()
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def unpublish_listing(self, *, listing_id: int, actor: User) -> Listing:
        listing = self.listings.get_by_id(listing_id, with_owner=True)
        if not listing or listing.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if listing.owner_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
        listing.status = ListingStatus.INACTIVE
        self.db.flush()
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def list_my_listings(
        self,
        *,
        actor: User,
        status_filter: ListingStatus | None = None,
        category_id: int | None = None,
        sort: str = "newest",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Listing], int]:
        return self.listings.list_by_owner(
            owner_id=actor.id,
            status=status_filter,
            category_id=category_id,
            sort=sort,
            page=page,
            page_size=page_size,
            with_owner=True,
        )

    def record_contact_intent(self, *, actor: User, listing_id: int) -> None:
        """Persist a contact intent and optionally notify the listing owner.

        Throttled to one successful request per (actor, listing) every 24 hours.
        Separate from chat: expresses interest in the seller's phone / callback, not a new_message notification.
        """
        listing = self.listings.get_by_id(listing_id)
        if not listing or listing.deleted_at is not None or listing.status != ListingStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
        if listing.owner_id == actor.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot request contact for your own listing",
            )

        stmt = (
            select(ListingContactIntent)
            .where(
                ListingContactIntent.actor_user_id == actor.id,
                ListingContactIntent.listing_id == listing_id,
            )
            .order_by(ListingContactIntent.created_at.desc())
            .limit(1)
        )
        prev = self.db.execute(stmt).scalar_one_or_none()
        if prev is not None:
            prev_at = prev.created_at
            if prev_at.tzinfo is None:
                prev_at = prev_at.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - prev_at
            if delta < timedelta(hours=CONTACT_INTENT_THROTTLE_HOURS):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Contact request limit: one per listing every 24 hours",
                )

        self.db.add(ListingContactIntent(actor_user_id=actor.id, listing_id=listing_id))
        self.db.flush()

        title = listing.title or "Listing"
        NotificationService(self.db).notify_contact_request(
            owner_id=listing.owner_id,
            requester_id=actor.id,
            listing_id=listing_id,
            listing_title=title,
            requester_name=actor.full_name or "Someone",
        )
        self.db.commit()

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

    @staticmethod
    def _build_images(images: list[dict]) -> list[ListingImage]:
        sorted_images = sorted(images, key=lambda i: (i.get("sort_order", 0), i.get("url", "")))
        return [
            ListingImage(url=str(image["url"]), sort_order=index)
            for index, image in enumerate(sorted_images)
        ]

    @staticmethod
    def _get_missing_publish_fields(listing: Listing) -> list[str]:
        missing: list[str] = []
        required = {
            "category_id": listing.category_id,
            "title": listing.title,
            "description": listing.description,
            "price": listing.price,
            "city": listing.city,
            "contact_phone": listing.contact_phone,
        }
        for key, value in required.items():
            if value is None:
                missing.append(key)
            elif isinstance(value, str) and value.strip() == "":
                missing.append(key)
        if not listing.images:
            missing.append("images")
        return missing

