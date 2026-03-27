from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.meta import CitySuggestion, CitySuggestionsResponse


router = APIRouter(prefix="/meta", tags=["meta"])


_KG_CITIES: list[tuple[str, int]] = [
    ("Bishkek", 100),
    ("Osh", 90),
    ("Jalal-Abad", 70),
    ("Karakol", 60),
    ("Tokmok", 55),
    ("Kara-Balta", 50),
    ("Naryn", 45),
    ("Talas", 40),
    ("Batken", 35),
    ("Kant", 30),
    ("Kyzyl-Kiya", 25),
    ("Balykchy", 20),
]


@router.get("/cities", response_model=CitySuggestionsResponse)
def cities(
    country: str = Query(default="KG", min_length=2, max_length=2),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    _: User = Depends(get_current_user),
) -> CitySuggestionsResponse:
    normalized_country = country.strip().upper()
    normalized_q = q.strip() if q else None
    if normalized_country != "KG":
        return CitySuggestionsResponse(country=normalized_country, q=normalized_q, items=[])

    items = _KG_CITIES
    if normalized_q:
        nq = normalized_q.lower()
        items = [c for c in items if nq in c[0].lower()]

    return CitySuggestionsResponse(
        country=normalized_country,
        q=normalized_q,
        items=[CitySuggestion(name=name, popularity=pop) for name, pop in items],
    )

