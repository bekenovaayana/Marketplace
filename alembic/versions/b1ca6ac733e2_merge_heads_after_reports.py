"""merge heads after reports

Revision ID: b1ca6ac733e2
Revises: e9239085200a, 9f2d4b7a1c55
Create Date: 2026-03-27 17:11:09.959134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1ca6ac733e2'
down_revision: Union[str, Sequence[str], None] = ('e9239085200a', '9f2d4b7a1c55')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
