"""add chat trust fields and indexes

Revision ID: c3e8b7f1a9d2
Revises: b7f3a1c4d2e8
Create Date: 2026-03-27 16:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3e8b7f1a9d2"
down_revision: Union[str, Sequence[str], None] = "b7f3a1c4d2e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("messages", sa.Column("client_message_id", sa.String(length=100), nullable=True))
    op.create_index("ix_messages_conversation_read_sender", "messages", ["conversation_id", "is_read", "sender_id"], unique=False)
    op.create_index("ix_messages_client_message_id", "messages", ["client_message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messages_client_message_id", table_name="messages")
    op.drop_index("ix_messages_conversation_read_sender", table_name="messages")
    op.drop_column("messages", "client_message_id")
    op.drop_column("users", "phone_verified")
    op.drop_column("users", "email_verified")
