from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.favorite import Favorite
from app.models.listing import Listing
from app.repositories.base import BaseRepository


class FavoriteRepository(BaseRepository[Favorite]):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, favorite: Favorite) -> Favorite:
        self.db.add(favorite)
        self.db.flush()
        self.db.refresh(favorite)
        return favorite

    def get_by_id(self, favorite_id: int) -> Favorite | None:
        return self.db.get(Favorite, favorite_id)

    def get_by_id_with_listing(self, favorite_id: int) -> Favorite | None:
        stmt = (
            select(Favorite)
            .where(Favorite.id == favorite_id)
            .options(
                joinedload(Favorite.listing).joinedload(Listing.owner),
                joinedload(Favorite.listing).joinedload(Listing.category),
                selectinload(Favorite.listing).selectinload(Listing.images),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def exists(self, *, user_id: int, listing_id: int) -> bool:
        stmt = select(Favorite.id).where(and_(Favorite.user_id == user_id, Favorite.listing_id == listing_id)).limit(1)
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def get_by_user_and_listing(self, *, user_id: int, listing_id: int) -> Favorite | None:
        stmt = select(Favorite).where(and_(Favorite.user_id == user_id, Favorite.listing_id == listing_id))
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, *, page: int = 1, page_size: int = 20, user_id: int | None = None) -> tuple[list[Favorite], int]:
        stmt = select(Favorite).order_by(Favorite.created_at.desc(), Favorite.id.desc())
        if user_id is not None:
            stmt = stmt.where(Favorite.user_id == user_id)
        return self._paginate(stmt, page=page, page_size=page_size)

    def list_with_listing(self, *, page: int = 1, page_size: int = 20, user_id: int) -> tuple[list[Favorite], int]:
        stmt = (
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc(), Favorite.id.desc())
            .options(
                joinedload(Favorite.listing).joinedload(Listing.owner),
                joinedload(Favorite.listing).joinedload(Listing.category),
                selectinload(Favorite.listing).selectinload(Listing.images),
            )
        )
        return self._paginate(stmt, page=page, page_size=page_size)

    def top_category_ids_for_user(self, *, user_id: int, limit: int = 5) -> list[int]:
        stmt = (
            select(Listing.category_id, func.count(Favorite.id).label("cnt"))
            .join(Listing, Favorite.listing_id == Listing.id)
            .where(
                Favorite.user_id == user_id,
                Listing.category_id.is_not(None),
                Listing.deleted_at.is_(None),
            )
            .group_by(Listing.category_id)
            .order_by(func.count(Favorite.id).desc(), Listing.category_id.asc())
            .limit(limit)
        )
        return [int(row[0]) for row in self.db.execute(stmt).all() if row[0] is not None]

    def update(self, favorite: Favorite, data: dict) -> Favorite:
        for k, v in data.items():
            setattr(favorite, k, v)
        self.db.flush()
        self.db.refresh(favorite)
        return favorite

    def delete(self, favorite: Favorite) -> None:
        self.db.delete(favorite)
        self.db.flush()

