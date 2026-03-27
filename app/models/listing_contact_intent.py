from __future__ import annotations

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ListingContactIntent(Base, TimestampMixin):
    """Auditable log for POST /listings/{id}/contact-intent; used for per-(user, listing) throttle."""

    __tablename__ = "listing_contact_intents"
    __table_args__ = (
        Index(
            "ix_listing_contact_intents_actor_listing_created",
            "actor_user_id",
            "listing_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True
    )
