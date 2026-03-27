"""add listing contact/geo and user phone

Revision ID: 6d5f73f8d9a1
Revises: 13213e44706b
Create Date: 2026-03-27 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6d5f73f8d9a1"
down_revision: Union[str, Sequence[str], None] = "13213e44706b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=True))

    op.add_column("listings", sa.Column("contact_phone", sa.String(length=32), nullable=True))
    op.add_column("listings", sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True))
    op.add_column("listings", sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True))
    op.create_index("ix_listings_price", "listings", ["price"], unique=False)

    op.execute("UPDATE listings SET contact_phone = '+0000000' WHERE contact_phone IS NULL")
    op.alter_column("listings", "contact_phone", existing_type=sa.String(length=32), nullable=False)


def downgrade() -> None:
    op.drop_index("ix_listings_price", table_name="listings")
    op.drop_column("listings", "longitude")
    op.drop_column("listings", "latitude")
    op.drop_column("listings", "contact_phone")
    op.drop_column("users", "phone")
