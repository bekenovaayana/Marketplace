from __future__ import annotations

from pydantic import Field

from app.schemas.common import BaseSchema


class CitySuggestion(BaseSchema):
    name: str = Field(min_length=1, max_length=120)
    popularity: int = Field(ge=0)


class CitySuggestionsResponse(BaseSchema):
    country: str = Field(default="KG", min_length=2, max_length=2)
    q: str | None = None
    items: list[CitySuggestion]

