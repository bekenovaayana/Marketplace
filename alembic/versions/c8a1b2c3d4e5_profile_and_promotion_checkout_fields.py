"""profile and promotion checkout fields

Revision ID: c8a1b2c3d4e5
Revises: f4c8d9e2a1b0
Create Date: 2026-03-27

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "f4c8d9e2a1b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users: split name fields (keep full_name for compatibility)
    op.add_column("users", sa.Column("first_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=120), nullable=True))

    # --- promotions: add checkout-oriented fields
    op.add_column("promotions", sa.Column("days", sa.Integer(), server_default="7", nullable=False))
    op.add_column("promotions", sa.Column("amount", sa.Numeric(precision=12, scale=2), server_default="0", nullable=False))
    op.add_column("promotions", sa.Column("payment_provider", sa.String(length=60), nullable=True))
    op.add_column("promotions", sa.Column("payment_intent_id", sa.String(length=120), nullable=True))

    # status enum: add pending_payment
    op.alter_column(
        "promotions",
        "status",
        existing_type=sa.Enum("active", "expired", "cancelled", name="promotion_status"),
        type_=sa.Enum("pending_payment", "active", "expired", "cancelled", name="promotion_status"),
        existing_nullable=False,
        server_default="pending_payment",
    )

    # backfill amount for existing rows
    op.execute("UPDATE promotions SET amount = purchased_price WHERE amount = 0")

    # indexes required by spec
    op.create_index("ix_promotions_user_status", "promotions", ["user_id", "status"], unique=False)
    op.create_index("ix_promotions_ends_at_status", "promotions", ["ends_at", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_promotions_ends_at_status", table_name="promotions")
    op.drop_index("ix_promotions_user_status", table_name="promotions")

    op.alter_column(
        "promotions",
        "status",
        existing_type=sa.Enum("pending_payment", "active", "expired", "cancelled", name="promotion_status"),
        type_=sa.Enum("active", "expired", "cancelled", name="promotion_status"),
        existing_nullable=False,
        server_default="active",
    )

    op.drop_column("promotions", "payment_intent_id")
    op.drop_column("promotions", "payment_provider")
    op.drop_column("promotions", "amount")
    op.drop_column("promotions", "days")

    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")

