from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampFields
from app.schemas.listing import ListingPublicRead


class FavoriteCreate(BaseSchema):
    listing_id: int = Field(gt=0)


class FavoriteUpdate(BaseSchema):
    pass


class FavoriteRead(BaseSchema, TimestampFields):
    id: int
    user_id: int
    listing_id: int


class FavoriteWithListingRead(FavoriteRead):
    listing: ListingPublicRead

