from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.report import Report, ReportStatus, ReportTargetType
from app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    def __init__(self, db: Session):
        super().__init__(db)

    def create(self, report: Report) -> Report:
        self.db.add(report)
        self.db.flush()
        self.db.refresh(report)
        return report

    def get_by_id(self, report_id: int) -> Report | None:
        stmt = (
            select(Report)
            .where(Report.id == report_id)
            .options(joinedload(Report.reporter), joinedload(Report.reviewed_by_admin))
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def find_pending(self, reporter_user_id: int, target_type: ReportTargetType, target_id: int) -> Report | None:
        stmt = select(Report).where(
            Report.reporter_user_id == reporter_user_id,
            Report.target_type == target_type,
            Report.target_id == target_id,
            Report.status == ReportStatus.PENDING,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_reporter(self, *, reporter_user_id: int, page: int, page_size: int) -> tuple[list[Report], int]:
        stmt = (
            select(Report)
            .where(Report.reporter_user_id == reporter_user_id)
            .options(joinedload(Report.reporter), joinedload(Report.reviewed_by_admin))
            .order_by(Report.created_at.desc(), Report.id.desc())
        )
        return self._paginate(stmt, page=page, page_size=page_size)

    def list_all(
        self,
        *,
        status_filter: ReportStatus | None,
        target_type_filter: ReportTargetType | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Report], int]:
        stmt = select(Report).options(joinedload(Report.reporter), joinedload(Report.reviewed_by_admin))
        if status_filter:
            stmt = stmt.where(Report.status == status_filter)
        if target_type_filter:
            stmt = stmt.where(Report.target_type == target_type_filter)
        stmt = stmt.order_by(Report.created_at.desc(), Report.id.desc())
        return self._paginate(stmt, page=page, page_size=page_size)

    def update_status(
        self,
        report_id: int,
        status: ReportStatus,
        resolution_note: str | None,
        reviewed_by_id: int,
        reviewed_at: datetime,
    ) -> Report | None:
        report = self.db.get(Report, report_id)
        if not report:
            return None
        report.status = status
        report.resolution_note = resolution_note
        report.reviewed_by_admin_id = reviewed_by_id
        report.reviewed_at = reviewed_at
        self.db.flush()
        self.db.refresh(report)
        return report
