from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        self.db.refresh(payment)
        return payment

    def get_by_id(self, payment_id: int) -> Payment | None:
        return self.db.get(Payment, payment_id)

    def list(self, *, page: int = 1, page_size: int = 20, user_id: int | None = None) -> tuple[list[Payment], int]:
        stmt = select(Payment).order_by(Payment.created_at.desc(), Payment.id.desc())
        if user_id is not None:
            stmt = stmt.where(Payment.user_id == user_id)
        return self._paginate(stmt, page=page, page_size=page_size)

    def update(self, payment: Payment, data: dict) -> Payment:
        for k, v in data.items():
            setattr(payment, k, v)
        self.db.flush()
        self.db.refresh(payment)
        return payment

    def delete(self, payment: Payment) -> None:
        self.db.delete(payment)
        self.db.flush()

