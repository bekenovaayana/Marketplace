from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, db: Session):
        self.db = db

    def _paginate(self, stmt: Select, *, page: int, page_size: int) -> tuple[list[T], int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 1

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        items = self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
        return items, int(total)

