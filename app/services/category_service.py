from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.category import CategoryPublicRead
from app.repositories.category_repository import CategoryRepository


class CategoryService:
    def __init__(self, db: Session):
        self.categories = CategoryRepository(db)

    def list_public(self, *, limit: int | None = None) -> list[CategoryPublicRead]:
        rows = self.categories.list_public_with_counts(limit=limit)
        return [
            CategoryPublicRead(
                id=category.id,
                name=category.name,
                slug=category.slug,
                listings_count=count,
            )
            for category, count in rows
        ]
