from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.report import Report, ReportReasonCode, ReportStatus, ReportTargetType
from app.models.user import User, UserStatus
from app.repositories.listing_repository import ListingRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.reports = ReportRepository(db)
        self.users = UserRepository(db)
        self.listings = ListingRepository(db)
        self.notifications = NotificationService(db)

    def _assert_admin(self, actor: User) -> None:
        if actor.status != UserStatus.ACTIVE or not actor.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    def _build_target_preview(self, report: Report) -> str | None:
        if report.target_type == ReportTargetType.LISTING:
            listing = self.listings.get_by_id(report.target_id)
            if listing:
                return f"Listing: {listing.title or f'#{listing.id}'}"
            return None
        user = self.users.get_by_id(report.target_id)
        if user:
            return f"User: {user.full_name}"
        return None

    def create_report(
        self,
        *,
        actor: User,
        target_type: ReportTargetType,
        target_id: int,
        reason_code: ReportReasonCode,
        reason_text: str | None,
    ) -> Report:
        if target_type == ReportTargetType.USER:
            if target_id == actor.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot report yourself")
            target_user = self.users.get_by_id(target_id)
            if not target_user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")
        else:
            target_listing = self.listings.get_by_id(target_id)
            if not target_listing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target listing not found")
            if target_listing.owner_id == actor.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot report your own listing")

        pending = self.reports.find_pending(actor.id, target_type, target_id)
        if pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pending report already exists for this target",
            )

        report = Report(
            reporter_user_id=actor.id,
            target_type=target_type,
            target_id=target_id,
            reason_code=reason_code,
            reason_text=reason_text.strip() if reason_text else None,
            status=ReportStatus.PENDING,
        )
        created = self.reports.create(report)
        self.db.commit()
        return self.reports.get_by_id(created.id) or created

    def list_my_reports(self, *, actor: User, page: int = 1, page_size: int = 20) -> tuple[list[Report], int]:
        items, total = self.reports.list_by_reporter(reporter_user_id=actor.id, page=page, page_size=page_size)
        for item in items:
            setattr(item, "target_preview", self._build_target_preview(item))
        return items, total

    def list_reports(
        self,
        *,
        actor: User,
        status_filter: ReportStatus | None,
        target_type_filter: ReportTargetType | None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Report], int]:
        self._assert_admin(actor)
        items, total = self.reports.list_all(
            status_filter=status_filter,
            target_type_filter=target_type_filter,
            page=page,
            page_size=page_size,
        )
        for item in items:
            setattr(item, "target_preview", self._build_target_preview(item))
        return items, total

    def get_report(self, *, actor: User, report_id: int) -> Report:
        self._assert_admin(actor)
        report = self.reports.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        setattr(report, "target_preview", self._build_target_preview(report))
        return report

    def resolve_report(self, *, actor: User, report_id: int, resolution_note: str | None) -> Report:
        self._assert_admin(actor)
        report = self.reports.update_status(
            report_id=report_id,
            status=ReportStatus.RESOLVED,
            resolution_note=resolution_note.strip() if resolution_note else None,
            reviewed_by_id=actor.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

        # Best effort notification for listing reports.
        if report.target_type == ReportTargetType.LISTING:
            listing = self.listings.get_by_id(report.target_id)
            if listing:
                note = (resolution_note or "").lower()
                try:
                    if any(token in note for token in ("reject", "rejected", "decline", "violation", "remove")):
                        self.notifications.notify_listing_rejected(
                            owner_id=listing.owner_id,
                            listing_id=listing.id,
                            listing_title=listing.title or f"Listing #{listing.id}",
                            reason=resolution_note,
                        )
                    else:
                        self.notifications.notify_listing_approved(
                            owner_id=listing.owner_id,
                            listing_id=listing.id,
                            listing_title=listing.title or f"Listing #{listing.id}",
                        )
                except Exception:
                    pass

        self.db.commit()
        resolved = self.reports.get_by_id(report.id) or report
        setattr(resolved, "target_preview", self._build_target_preview(resolved))
        return resolved

    def dismiss_report(self, *, actor: User, report_id: int, resolution_note: str | None) -> Report:
        self._assert_admin(actor)
        report = self.reports.update_status(
            report_id=report_id,
            status=ReportStatus.DISMISSED,
            resolution_note=resolution_note.strip() if resolution_note else None,
            reviewed_by_id=actor.id,
            reviewed_at=datetime.now(timezone.utc),
        )
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        self.db.commit()
        dismissed = self.reports.get_by_id(report.id) or report
        setattr(dismissed, "target_preview", self._build_target_preview(dismissed))
        return dismissed
