from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.listing import Listing, ListingStatus
from app.repositories.base import BaseRepository


class ListingRepository(BaseRepository[Listing]):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, listing: Listing) -> Listing:
        self.db.add(listing)
        self.db.flush()
        self.db.refresh(listing)
        return listing

    def get_by_id(self, listing_id: int, *, with_owner: bool = False) -> Listing | None:
        if not with_owner:
            return self.db.get(Listing, listing_id)
        stmt = (
            select(Listing)
            .where(Listing.id == listing_id)
            .options(joinedload(Listing.owner), joinedload(Listing.category), selectinload(Listing.images))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, *, page: int = 1, page_size: int = 20, with_owner: bool = False) -> tuple[list[Listing], int]:
        stmt = select(Listing).order_by(Listing.created_at.desc(), Listing.id.desc())
        if with_owner:
            stmt = stmt.options(joinedload(Listing.owner), joinedload(Listing.category), selectinload(Listing.images))
        return self._paginate(stmt, page=page, page_size=page_size)

    def list_public_active(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        with_owner: bool = False,
    ) -> tuple[list[Listing], int]:
        stmt = (
            select(Listing)
            .where(Listing.status == ListingStatus.ACTIVE, Listing.deleted_at.is_(None))
            .order_by(Listing.is_boosted.desc(), Listing.created_at.desc(), Listing.id.desc())
        )
        if with_owner:
            stmt = stmt.options(joinedload(Listing.owner), joinedload(Listing.category), selectinload(Listing.images))
        return self._paginate(stmt, page=page, page_size=page_size)

    def update(self, listing: Listing, data: dict) -> Listing:
        for k, v in data.items():
            setattr(listing, k, v)
        self.db.flush()
        self.db.refresh(listing)
        return listing

    def delete(self, listing: Listing) -> None:
        self.db.delete(listing)
        self.db.flush()

