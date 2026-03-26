from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.favorite import Favorite
from app.models.listing import ListingStatus
from app.models.user import User
from app.repositories.favorite_repository import FavoriteRepository
from app.repositories.listing_repository import ListingRepository


class FavoriteService:
    def __init__(self, db: Session):
        self.db = db
        self.favorites = FavoriteRepository(db)
        self.listings = ListingRepository(db)

    def add_favorite(self, *, actor: User, listing_id: int) -> Favorite:
        listing = self.listings.get_by_id(listing_id)
        if not listing or listing.deleted_at is not None or listing.status != ListingStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        if self.favorites.exists(user_id=actor.id, listing_id=listing_id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already favorited")

        fav = Favorite(user_id=actor.id, listing_id=listing_id)
        self.favorites.create(fav)
        self.db.commit()
        return fav

    def remove_favorite(self, *, actor: User, listing_id: int) -> None:
        fav = self.favorites.get_by_user_and_listing(user_id=actor.id, listing_id=listing_id)
        if not fav:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
        self.favorites.delete(fav)
        self.db.commit()

    def list_favorites(self, *, actor: User, page: int = 1, page_size: int = 20) -> tuple[list[Favorite], int]:
        return self.favorites.list_with_listing(user_id=actor.id, page=page, page_size=page_size)

    def get_favorite(self, *, favorite_id: int) -> Favorite:
        fav = self.favorites.get_by_id_with_listing(favorite_id)
        if not fav:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found")
        return fav

