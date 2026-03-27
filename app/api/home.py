from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_optional_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.home import HomeRead
from app.services.home_service import HomeService

router = APIRouter(prefix="/home", tags=["home"])


@router.get("", response_model=HomeRead)
def get_home(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    categories_limit: int = Query(default=20, ge=1, le=100),
    items_limit: int = Query(default=20, ge=1, le=100),
    city: str | None = Query(default=None, description="Optional city scope for latest/recommended", example="Bishkek"),
    category_id: int | None = Query(default=None, gt=0, description="Optional category scope", example=1),
) -> HomeRead:
    return HomeService(db).get_home(
        categories_limit=categories_limit,
        items_limit=items_limit,
        city=city,
        category_id=category_id,
        actor=current_user,
    )
