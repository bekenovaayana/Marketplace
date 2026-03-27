from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.category import CategoryPublicRead
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryPublicRead])
def list_categories(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CategoryPublicRead]:
    return CategoryService(db).list_public(limit=limit)
