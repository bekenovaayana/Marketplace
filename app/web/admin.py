from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.session import get_db
from app.models.report import ReportStatus, ReportTargetType
from app.models.user import User, UserStatus
from app.repositories.user_repository import UserRepository
from app.schemas.report import ReportResolveRequest
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-panel"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _set_flash(request: Request, level: str, message: str) -> None:
    flashes = request.session.get("admin_flashes", [])
    flashes.append({"level": level, "message": message})
    request.session["admin_flashes"] = flashes


def _pop_flashes(request: Request) -> list[dict]:
    flashes = request.session.get("admin_flashes", [])
    request.session["admin_flashes"] = []
    return flashes


def _ensure_csrf_token(request: Request) -> str:
    token = request.session.get("admin_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["admin_csrf_token"] = token
    return token


def _validate_csrf(request: Request, token: str | None) -> None:
    expected = request.session.get("admin_csrf_token")
    if not expected or not token or expected != token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


def _csrf_error_response(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="admin/error.html",
        context={
            "title": "Forbidden",
            "message": "Invalid CSRF token",
            "flashes": _pop_flashes(request),
            "csrf_token": _ensure_csrf_token(request),
            "admin_user": None,
        },
        status_code=status.HTTP_403_FORBIDDEN,
    )


def get_admin_session_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("admin_user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    user = UserRepository(db).get_by_id(int(user_id))
    if not user or user.status != UserStatus.ACTIVE or not user.is_admin:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def _redirect_to_login() -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request) -> HTMLResponse:
    if request.session.get("admin_user_id"):
        return RedirectResponse(url="/admin/reports", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={
            "title": "Admin Login",
            "flashes": _pop_flashes(request),
            "csrf_token": _ensure_csrf_token(request),
        },
    )


@router.post("/login", include_in_schema=False)
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        _validate_csrf(request, csrf_token)
    except HTTPException:
        _set_flash(request, "error", "Invalid CSRF token")
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    user = UserRepository(db).get_by_email(email.strip().lower())
    if not user or not verify_password(password, user.password_hash):
        _set_flash(request, "error", "Invalid credentials")
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    if user.status != UserStatus.ACTIVE:
        _set_flash(request, "error", "Inactive account")
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    if not user.is_admin:
        _set_flash(request, "error", "Admin access required")
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    request.session["admin_user_id"] = user.id
    _set_flash(request, "success", "Logged in successfully")
    return RedirectResponse(url="/admin/reports", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout", include_in_schema=False)
def logout(request: Request, csrf_token: str = Form(...)) -> RedirectResponse:
    try:
        _validate_csrf(request, csrf_token)
    except HTTPException:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("", include_in_schema=False)
def admin_index() -> RedirectResponse:
    return RedirectResponse(url="/admin/reports", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/reports", response_class=HTMLResponse, include_in_schema=False)
def reports_list(
    request: Request,
    status_filter: ReportStatus | None = Query(default=None, alias="status"),
    target_type_filter: ReportTargetType | None = Query(default=None, alias="target_type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        admin_user = get_admin_session_user(request, db)
    except HTTPException:
        return _redirect_to_login()

    items, total = ReportService(db).list_reports(
        actor=admin_user,
        status_filter=status_filter,
        target_type_filter=target_type_filter,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return templates.TemplateResponse(
        request=request,
        name="admin/reports_list.html",
        context={
            "title": "Reports",
            "admin_user": admin_user,
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "status_filter": status_filter.value if status_filter else "",
            "target_type_filter": target_type_filter.value if target_type_filter else "",
            "status_options": [e.value for e in ReportStatus],
            "target_type_options": [e.value for e in ReportTargetType],
            "flashes": _pop_flashes(request),
            "csrf_token": _ensure_csrf_token(request),
        },
    )


@router.get("/reports/{report_id}", response_class=HTMLResponse, include_in_schema=False)
def report_detail(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        admin_user = get_admin_session_user(request, db)
    except HTTPException:
        return _redirect_to_login()

    try:
        report = ReportService(db).get_report(actor=admin_user, report_id=report_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            _set_flash(request, "error", "Report not found")
            return RedirectResponse(url="/admin/reports", status_code=status.HTTP_303_SEE_OTHER)
        raise

    return templates.TemplateResponse(
        request=request,
        name="admin/report_detail.html",
        context={
            "title": f"Report #{report.id}",
            "admin_user": admin_user,
            "report": report,
            "flashes": _pop_flashes(request),
            "csrf_token": _ensure_csrf_token(request),
        },
    )


@router.post("/reports/{report_id}/resolve", include_in_schema=False)
def resolve_report(
    report_id: int,
    request: Request,
    resolution_note: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        admin_user = get_admin_session_user(request, db)
    except HTTPException:
        return _redirect_to_login()
    try:
        _validate_csrf(request, csrf_token)
    except HTTPException:
        return _csrf_error_response(request)

    report = ReportService(db).resolve_report(
        actor=admin_user,
        report_id=report_id,
        resolution_note=ReportResolveRequest(resolution_note=resolution_note).resolution_note,
    )
    logger.info("Admin moderation action: admin_id=%s report_id=%s action=resolve", admin_user.id, report.id)
    _set_flash(request, "success", f"Report #{report.id} resolved")
    return RedirectResponse(url=f"/admin/reports/{report_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/reports/{report_id}/dismiss", include_in_schema=False)
def dismiss_report(
    report_id: int,
    request: Request,
    resolution_note: str | None = Form(default=None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        admin_user = get_admin_session_user(request, db)
    except HTTPException:
        return _redirect_to_login()
    try:
        _validate_csrf(request, csrf_token)
    except HTTPException:
        return _csrf_error_response(request)

    report = ReportService(db).dismiss_report(
        actor=admin_user,
        report_id=report_id,
        resolution_note=ReportResolveRequest(resolution_note=resolution_note).resolution_note,
    )
    logger.info("Admin moderation action: admin_id=%s report_id=%s action=dismiss", admin_user.id, report.id)
    _set_flash(request, "success", f"Report #{report.id} dismissed")
    return RedirectResponse(url=f"/admin/reports/{report_id}", status_code=status.HTTP_303_SEE_OTHER)
