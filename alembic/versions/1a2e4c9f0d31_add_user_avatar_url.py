"""add user avatar_url

Revision ID: 1a2e4c9f0d31
Revises: 6d5f73f8d9a1
Create Date: 2026-03-27 14:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1a2e4c9f0d31"
down_revision: Union[str, Sequence[str], None] = "6d5f73f8d9a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
