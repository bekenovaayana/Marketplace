from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
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

