"""make listing fields nullable for drafts

Revision ID: b7f3a1c4d2e8
Revises: 1a2e4c9f0d31
Create Date: 2026-03-27 15:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7f3a1c4d2e8"
down_revision: Union[str, Sequence[str], None] = "1a2e4c9f0d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("listings", "category_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("listings", "title", existing_type=sa.String(length=200), nullable=True)
    op.alter_column("listings", "description", existing_type=sa.Text(), nullable=True)
    op.alter_column("listings", "price", existing_type=sa.Numeric(precision=12, scale=2), nullable=True)
    op.alter_column("listings", "city", existing_type=sa.String(length=120), nullable=True)
    op.alter_column("listings", "contact_phone", existing_type=sa.String(length=32), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM listings WHERE category_id IS NULL")
    op.execute("DELETE FROM listings WHERE title IS NULL")
    op.execute("DELETE FROM listings WHERE description IS NULL")
    op.execute("DELETE FROM listings WHERE price IS NULL")
    op.execute("DELETE FROM listings WHERE city IS NULL")
    op.execute("DELETE FROM listings WHERE contact_phone IS NULL")

    op.alter_column("listings", "contact_phone", existing_type=sa.String(length=32), nullable=False)
    op.alter_column("listings", "city", existing_type=sa.String(length=120), nullable=False)
    op.alter_column("listings", "price", existing_type=sa.Numeric(precision=12, scale=2), nullable=False)
    op.alter_column("listings", "description", existing_type=sa.Text(), nullable=False)
    op.alter_column("listings", "title", existing_type=sa.String(length=200), nullable=False)
    op.alter_column("listings", "category_id", existing_type=sa.Integer(), nullable=False)
