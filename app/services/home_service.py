from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.home import HomeRead
from app.services.category_service import CategoryService
from app.services.listing_service import ListingService


class HomeService:
    def __init__(self, db: Session):
        self.db = db
        self.categories = CategoryService(db)
        self.listings = ListingService(db)

    def get_home(
        self,
        *,
        categories_limit: int = 20,
        items_limit: int = 20,
        city: str | None = None,
        category_id: int | None = None,
        actor: User | None = None,
    ) -> HomeRead:
        recommended, _, _ = self.listings.list_public_active(
            page=1,
            page_size=items_limit,
            city=city,
            category_id=category_id,
            sort="recommended",
            actor=actor,
            with_owner=True,
        )
        latest, _, _ = self.listings.list_public_active(
            page=1,
            page_size=items_limit,
            city=city,
            category_id=category_id,
            sort="newest",
            with_owner=True,
        )
        return HomeRead(
            categories=self.categories.list_public(limit=categories_limit),
            recommended=recommended,
            latest=latest,
        )
