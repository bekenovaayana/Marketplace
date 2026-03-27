from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.category import Category
from app.models.listing import Listing, ListingStatus
from app.models.promotion import Promotion, PromotionStatus
from app.repositories.base import BaseRepository


class ListingRepository(BaseRepository[Listing]):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, listing: Listing) -> Listing:
        self.db.add(listing)
        self.db.flush()
        self.db.refresh(listing)
        return listing

    def get_by_id(self, listing_id: int, *, with_owner: bool = False) -> Listing | None:
        if not with_owner:
            return self.db.get(Listing, listing_id)
        stmt = (
            select(Listing)
            .where(Listing.id == listing_id)
            .options(joinedload(Listing.owner), joinedload(Listing.category), selectinload(Listing.images))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, *, page: int = 1, page_size: int = 20, with_owner: bool = False) -> tuple[list[Listing], int]:
        stmt = select(Listing).order_by(Listing.created_at.desc(), Listing.id.desc())
        if with_owner:
            stmt = stmt.options(joinedload(Listing.owner), joinedload(Listing.category), selectinload(Listing.images))
        return self._paginate(stmt, page=page, page_size=page_size)

    def list_by_owner(
        self,
        *,
        owner_id: int,
        status: ListingStatus | None = None,
        category_id: int | None = None,
        sort: str = "newest",
        page: int = 1,
        page_size: int = 20,
        with_owner: bool = True,
    ) -> tuple[list[Listing], int]:
        active_promo_exists = (
            select(Promotion.id)
            .where(
                Promotion.listing_id == Listing.id,
                Promotion.status == PromotionStatus.ACTIVE,
                Promotion.ends_at > func.now(),
            )
            .exists()
        )
        promo_rank = case((active_promo_exists, 0), else_=1)

        stmt = select(Listing).where(Listing.owner_id == owner_id, Listing.deleted_at.is_(None))
        if status is not None:
            stmt = stmt.where(Listing.status == status)
        if category_id is not None:
            stmt = stmt.where(Listing.category_id == category_id)

        if sort == "price_asc":
            stmt = stmt.order_by(
                promo_rank.asc(),
                Listing.price.asc().nulls_last(),
                Listing.created_at.desc(),
                Listing.id.desc(),
            )
        elif sort == "price_desc":
            stmt = stmt.order_by(
                promo_rank.asc(),
                Listing.price.desc().nulls_last(),
                Listing.created_at.desc(),
                Listing.id.desc(),
            )
        else:
            stmt = stmt.order_by(promo_rank.asc(), Listing.created_at.desc(), Listing.id.desc())

        if with_owner:
            stmt = stmt.options(joinedload(Listing.owner), joinedload(Listing.category), selectinload(Listing.images))
        return self._paginate(stmt, page=page, page_size=page_size)

    def count_active_by_owner(self, *, owner_id: int) -> int:
        stmt = select(func.count(Listing.id)).where(
            Listing.owner_id == owner_id,
            Listing.status == ListingStatus.ACTIVE,
            Listing.deleted_at.is_(None),
        )
        return int(self.db.execute(stmt).scalar_one())

    def list_public_active(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
        category_id: int | None = None,
        city: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        sort: str = "newest",
        affinity_category_ids: list[int] | None = None,
        with_owner: bool = False,
    ) -> tuple[list[Listing], int]:
        stmt = select(Listing).where(Listing.status == ListingStatus.ACTIVE, Listing.deleted_at.is_(None))

        active_promo_exists = (
            select(Promotion.id)
            .where(
                Promotion.listing_id == Listing.id,
                Promotion.status == PromotionStatus.ACTIVE,
                Promotion.ends_at > func.now(),
            )
            .exists()
        )
        promo_rank = case((active_promo_exists, 0), else_=1)

        if q:
            q_like = f"%{q}%"
            stmt = stmt.where((Listing.title.ilike(q_like)) | (Listing.description.ilike(q_like)))
        if category_id:
            stmt = stmt.where(Listing.category_id == category_id)
        if city:
            city_exact = city.lower()
            city_prefix = f"{city_exact}%"
            stmt = stmt.where((Listing.city.ilike(city_exact)) | (Listing.city.ilike(city_prefix)))
        if min_price is not None:
            stmt = stmt.where(Listing.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Listing.price <= max_price)

        if sort == "price_asc":
            stmt = stmt.order_by(promo_rank.asc(), Listing.price.asc(), Listing.id.desc())
        elif sort == "price_desc":
            stmt = stmt.order_by(promo_rank.asc(), Listing.price.desc(), Listing.id.desc())
        elif sort == "recommended":
            affinity_case = case(
                (Listing.category_id.in_(affinity_category_ids or []), 0),
                else_=1,
            )
            stmt = stmt.order_by(
                promo_rank.asc(),
                affinity_case.asc(),
                Listing.created_at.desc(),
                Listing.id.desc(),
            )
        elif sort == "relevance" and q:
            q_prefix = f"{q}%"
            q_like = f"%{q}%"
            relevance_rank = case(
                (Listing.title.ilike(q_prefix), 0),
                (Listing.title.ilike(q_like), 1),
                (Listing.description.ilike(q_like), 2),
                else_=3,
            )
            stmt = stmt.order_by(promo_rank.asc(), relevance_rank.asc(), Listing.created_at.desc(), Listing.id.desc())
        else:
            stmt = stmt.order_by(promo_rank.asc(), Listing.created_at.desc(), Listing.id.desc())

        if with_owner:
            stmt = stmt.options(joinedload(Listing.owner), joinedload(Listing.category), selectinload(Listing.images))
        return self._paginate(stmt, page=page, page_size=page_size)

    def get_public_facets(
        self,
        *,
        q: str | None = None,
        category_id: int | None = None,
        city: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
    ) -> dict:
        base = select(Listing).where(Listing.status == ListingStatus.ACTIVE, Listing.deleted_at.is_(None))
        if q:
            q_like = f"%{q}%"
            base = base.where((Listing.title.ilike(q_like)) | (Listing.description.ilike(q_like)))
        if category_id:
            base = base.where(Listing.category_id == category_id)
        if city:
            city_exact = city.lower()
            city_prefix = f"{city_exact}%"
            base = base.where((Listing.city.ilike(city_exact)) | (Listing.city.ilike(city_prefix)))
        if min_price is not None:
            base = base.where(Listing.price >= min_price)
        if max_price is not None:
            base = base.where(Listing.price <= max_price)

        filtered_subquery = base.subquery()
        price_row = self.db.execute(
            select(func.min(filtered_subquery.c.price), func.max(filtered_subquery.c.price))
        ).one()
        cities_rows = self.db.execute(
            select(filtered_subquery.c.city, func.count().label("cnt"))
            .where(filtered_subquery.c.city.is_not(None))
            .group_by(filtered_subquery.c.city)
            .order_by(func.count().desc(), filtered_subquery.c.city.asc())
            .limit(10)
        ).all()
        category_rows = self.db.execute(
            select(Category.id, Category.slug, func.count(filtered_subquery.c.id).label("cnt"))
            .join(filtered_subquery, filtered_subquery.c.category_id == Category.id)
            .group_by(Category.id, Category.slug)
            .order_by(func.count(filtered_subquery.c.id).desc(), Category.id.asc())
            .limit(10)
        ).all()

        return {
            "price_min": float(price_row[0]) if price_row[0] is not None else None,
            "price_max": float(price_row[1]) if price_row[1] is not None else None,
            "cities": [{"city": row[0], "count": int(row[1])} for row in cities_rows],
            "categories": [{"id": int(row[0]), "slug": row[1], "count": int(row[2])} for row in category_rows],
        }

    def update(self, listing: Listing, data: dict) -> Listing:
        for k, v in data.items():
            setattr(listing, k, v)
        self.db.flush()
        self.db.refresh(listing)
        return listing

    def increment_view_count(self, *, listing: Listing) -> Listing:
        listing.view_count = (listing.view_count or 0) + 1
        self.db.flush()
        self.db.refresh(listing)
        return listing

    def delete(self, listing: Listing) -> None:
        self.db.delete(listing)
        self.db.flush()

