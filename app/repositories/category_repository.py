from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.listing import Listing, ListingStatus
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, category: Category) -> Category:
        self.db.add(category)
        self.db.flush()
        self.db.refresh(category)
        return category

    def get_by_id(self, category_id: int) -> Category | None:
        return self.db.get(Category, category_id)

    def get_by_slug(self, slug: str) -> Category | None:
        return self.db.execute(select(Category).where(Category.slug == slug)).scalar_one_or_none()

    def list_public_with_counts(self, *, limit: int | None = None) -> list[tuple[Category, int]]:
        stmt = (
            select(Category, func.count(Listing.id))
            .outerjoin(
                Listing,
                and_(
                    Listing.category_id == Category.id,
                    Listing.status == ListingStatus.ACTIVE,
                    Listing.deleted_at.is_(None),
                ),
            )
            .where(Category.is_active.is_(True))
            .group_by(Category.id)
            .order_by(Category.display_order.asc(), Category.id.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return [(row[0], int(row[1])) for row in self.db.execute(stmt).all()]

    def list(self, *, page: int = 1, page_size: int = 50) -> tuple[list[Category], int]:
        stmt = select(Category).order_by(Category.display_order.asc(), Category.id.asc())
        return self._paginate(stmt, page=page, page_size=page_size)

    def update(self, category: Category, data: dict) -> Category:
        for k, v in data.items():
            setattr(category, k, v)
        self.db.flush()
        self.db.refresh(category)
        return category

    def delete(self, category: Category) -> None:
        self.db.delete(category)
        self.db.flush()

