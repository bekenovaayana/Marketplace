"""add reports table and users.is_admin

Revision ID: 9f2d4b7a1c55
Revises: c3e8b7f1a9d2
Create Date: 2026-03-27 20:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2d4b7a1c55"
down_revision: Union[str, Sequence[str], None] = "c3e8b7f1a9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


report_target_type = sa.Enum("listing", "user", name="report_target_type")
report_reason_code = sa.Enum(
    "spam",
    "fake_listing",
    "scam",
    "duplicate",
    "offensive_content",
    "prohibited_item",
    "harassment",
    "other",
    name="report_reason_code",
)
report_status = sa.Enum("pending", "under_review", "resolved", "dismissed", name="report_status")


def upgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="0"))

    report_target_type.create(op.get_bind(), checkfirst=True)
    report_reason_code.create(op.get_bind(), checkfirst=True)
    report_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reporter_user_id", sa.Integer(), nullable=False),
        sa.Column("target_type", report_target_type, nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason_code", report_reason_code, nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("status", report_status, nullable=False, server_default="pending"),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_admin_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_reporter_user_id"), "reports", ["reporter_user_id"], unique=False)
    op.create_index("ix_reports_target", "reports", ["target_type", "target_id"], unique=False)
    op.create_index("ix_reports_status", "reports", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_target", table_name="reports")
    op.drop_index(op.f("ix_reports_reporter_user_id"), table_name="reports")
    op.drop_table("reports")

    report_status.drop(op.get_bind(), checkfirst=True)
    report_reason_code.drop(op.get_bind(), checkfirst=True)
    report_target_type.drop(op.get_bind(), checkfirst=True)

    op.drop_column("users", "is_admin")
