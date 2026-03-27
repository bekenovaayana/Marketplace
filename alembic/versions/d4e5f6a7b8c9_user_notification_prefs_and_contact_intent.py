"""user notification prefs, contact intent, notification enum

Revision ID: d4e5f6a7b8c9
Revises: c8a1b2c3d4e5
Create Date: 2026-03-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c8a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_old_notification_enum = (
    "new_message",
    "listing_approved",
    "listing_rejected",
    "report_status_changed",
    "payment_successful",
    "promotion_activated",
    "promotion_expired",
)

_new_notification_enum = _old_notification_enum + ("listing_favorited", "contact_request")


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("theme", sa.String(length=16), server_default="system", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("notify_new_message", sa.Boolean(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("notify_contact_request", sa.Boolean(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("notify_listing_favorited", sa.Boolean(), server_default=sa.text("1"), nullable=False),
    )

    op.create_table(
        "listing_contact_intents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_listing_contact_intents_actor_listing_created",
        "listing_contact_intents",
        ["actor_user_id", "listing_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_listing_contact_intents_actor_user_id"),
        "listing_contact_intents",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_listing_contact_intents_listing_id"),
        "listing_contact_intents",
        ["listing_id"],
        unique=False,
    )

    op.alter_column(
        "notifications",
        "notification_type",
        existing_type=sa.Enum(*_old_notification_enum, name="notification_type"),
        type_=sa.Enum(*_new_notification_enum, name="notification_type"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "notifications",
        "notification_type",
        existing_type=sa.Enum(*_new_notification_enum, name="notification_type"),
        type_=sa.Enum(*_old_notification_enum, name="notification_type"),
        existing_nullable=False,
    )

    op.drop_index(op.f("ix_listing_contact_intents_listing_id"), table_name="listing_contact_intents")
    op.drop_index(op.f("ix_listing_contact_intents_actor_user_id"), table_name="listing_contact_intents")
    op.drop_index("ix_listing_contact_intents_actor_listing_created", table_name="listing_contact_intents")
    op.drop_table("listing_contact_intents")

    op.drop_column("users", "notify_listing_favorited")
    op.drop_column("users", "notify_contact_request")
    op.drop_column("users", "notify_new_message")
    op.drop_column("users", "theme")
