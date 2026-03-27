from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_admin_user, get_current_user
from app.db.session import get_db
from app.models.report import ReportStatus, ReportTargetType
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.report import ReportCreate, ReportRead, ReportResolveRequest
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create report",
    description="Report a listing or user for moderation review.",
)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportRead:
    return ReportService(db).create_report(
        actor=current_user,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason_code=payload.reason_code,
        reason_text=payload.reason_text,
    )


@router.get(
    "/me",
    response_model=Page[ReportRead],
    summary="List my reports",
    description="Returns reports submitted by current user (paginated).",
)
def list_my_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ReportRead]:
    items, total = ReportService(db).list_my_reports(actor=current_user, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))


@router.get(
    "",
    response_model=Page[ReportRead],
    summary="List all reports (admin)",
    description="Admin-only endpoint. Filter by status and target type.",
)
def list_reports(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
    status_filter: ReportStatus | None = Query(default=None, alias="status"),
    target_type_filter: ReportTargetType | None = Query(default=None, alias="target_type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ReportRead]:
    items, total = ReportService(db).list_reports(
        actor=admin_user,
        status_filter=status_filter,
        target_type_filter=target_type_filter,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(items=items, meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages))


@router.get(
    "/{report_id}",
    response_model=ReportRead,
    summary="Get report detail (admin)",
    description="Admin-only report detail with reporter info and target preview.",
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> ReportRead:
    return ReportService(db).get_report(actor=admin_user, report_id=report_id)


@router.post(
    "/{report_id}/resolve",
    response_model=ReportRead,
    summary="Resolve report (admin)",
    description="Admin-only action. Sets status to resolved and records reviewer metadata.",
)
def resolve_report(
    report_id: int,
    payload: ReportResolveRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> ReportRead:
    return ReportService(db).resolve_report(
        actor=admin_user,
        report_id=report_id,
        resolution_note=payload.resolution_note,
    )


@router.post(
    "/{report_id}/dismiss",
    response_model=ReportRead,
    summary="Dismiss report (admin)",
    description="Admin-only action. Sets status to dismissed and records reviewer metadata.",
)
def dismiss_report(
    report_id: int,
    payload: ReportResolveRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> ReportRead:
    return ReportService(db).dismiss_report(
        actor=admin_user,
        report_id=report_id,
        resolution_note=payload.resolution_note,
    )
