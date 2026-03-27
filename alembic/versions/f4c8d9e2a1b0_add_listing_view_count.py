"""add_listing_view_count

Revision ID: f4c8d9e2a1b0
Revises: b1ca6ac733e2
Create Date: 2026-03-27 23:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4c8d9e2a1b0"
down_revision: Union[str, Sequence[str], None] = "b1ca6ac733e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("listings", "view_count")
