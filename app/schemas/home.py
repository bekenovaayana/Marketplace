from __future__ import annotations

from app.schemas.category import CategoryPublicRead
from app.schemas.common import BaseSchema
from app.schemas.listing import ListingPublicRead


class HomeRead(BaseSchema):
    categories: list[CategoryPublicRead]
    recommended: list[ListingPublicRead]
    latest: list[ListingPublicRead]
