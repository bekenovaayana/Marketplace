from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ReportTargetType(str, enum.Enum):
    LISTING = "listing"
    USER = "user"


class ReportReasonCode(str, enum.Enum):
    SPAM = "spam"
    FAKE_LISTING = "fake_listing"
    SCAM = "scam"
    DUPLICATE = "duplicate"
    OFFENSIVE_CONTENT = "offensive_content"
    PROHIBITED_ITEM = "prohibited_item"
    HARASSMENT = "harassment"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type: Mapped[ReportTargetType] = mapped_column(
        Enum(ReportTargetType, name="report_target_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[ReportReasonCode] = mapped_column(
        Enum(ReportReasonCode, name="report_reason_code", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=ReportStatus.PENDING.value,
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reporter = relationship("User", foreign_keys=[reporter_user_id], back_populates="reports_submitted")
    reviewed_by_admin = relationship("User", foreign_keys=[reviewed_by_admin_id], back_populates="reports_reviewed")


Index("ix_reports_target", Report.target_type, Report.target_id)
Index("ix_reports_status", Report.status)
