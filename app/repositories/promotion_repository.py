from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.promotion import Promotion
from app.repositories.base import BaseRepository


class PromotionRepository(BaseRepository[Promotion]):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, promotion: Promotion) -> Promotion:
        self.db.add(promotion)
        self.db.flush()
        self.db.refresh(promotion)
        return promotion

    def get_by_id(self, promotion_id: int) -> Promotion | None:
        return self.db.get(Promotion, promotion_id)

    def list(self, *, page: int = 1, page_size: int = 20, user_id: int | None = None) -> tuple[list[Promotion], int]:
        stmt = select(Promotion).order_by(Promotion.created_at.desc(), Promotion.id.desc())
        if user_id is not None:
            stmt = stmt.where(Promotion.user_id == user_id)
        return self._paginate(stmt, page=page, page_size=page_size)

    def update(self, promotion: Promotion, data: dict) -> Promotion:
        for k, v in data.items():
            setattr(promotion, k, v)
        self.db.flush()
        self.db.refresh(promotion)
        return promotion

    def delete(self, promotion: Promotion) -> None:
        self.db.delete(promotion)
        self.db.flush()

