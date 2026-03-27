from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_optional_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page, PageMeta
from app.schemas.listing import ListingRead
from app.schemas.user import (
    AvatarUploadResponse,
    ChangePasswordRequest,
    DetailMessage,
    UserCompletenessRead,
    UserPublicRead,
    UserRead,
    UserUpdate,
)
from app.services.upload_service import UploadService
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user


@router.put("/me", response_model=UserRead)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserService(db).update_me(actor=current_user, data=payload.model_dump(exclude_unset=True))


@router.patch("/me", response_model=UserRead, summary="Partially update my profile")
def patch_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserService(db).update_me(actor=current_user, data=payload.model_dump(exclude_unset=True))


@router.post(
    "/me/avatar",
    response_model=AvatarUploadResponse,
    summary="Upload profile avatar",
    description="Upload a JPEG/PNG/WEBP avatar image up to 10 MB. Optional crop fields can be provided.",
)
def upload_avatar(
    file: UploadFile = File(..., description="Avatar image file"),
    crop_x: int | None = Form(default=None, description="Optional crop rectangle X offset"),
    crop_y: int | None = Form(default=None, description="Optional crop rectangle Y offset"),
    crop_width: int | None = Form(default=None, description="Optional crop rectangle width"),
    crop_height: int | None = Form(default=None, description="Optional crop rectangle height"),
    crop_rotation: float | None = Form(default=None, description="Optional clockwise crop rotation in degrees"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AvatarUploadResponse:
    old_url = current_user.avatar_url
    uploaded = UploadService().upload_avatar_image_with_optional_crop(
        upload_file=file,
        crop_x=crop_x,
        crop_y=crop_y,
        crop_width=crop_width,
        crop_height=crop_height,
        crop_rotation=crop_rotation,
    )
    UserService(db).set_avatar(actor=current_user, avatar_url=uploaded.url)

    # Best-effort delete of previous avatar file if it was stored locally.
    if old_url and old_url.startswith(f"{settings.UPLOADS_URL_PREFIX}/users/avatars/"):
        try:
            rel = old_url.removeprefix(f"{settings.UPLOADS_URL_PREFIX}/").lstrip("/")
            path = (Path(settings.UPLOADS_DIR) / rel).resolve()
            uploads_root = Path(settings.UPLOADS_DIR).resolve()
            if uploads_root in path.parents and path.exists() and path.is_file():
                path.unlink(missing_ok=True)
        except Exception:
            pass

    return AvatarUploadResponse(avatar_url=uploaded.url, content_type=uploaded.content_type, size_bytes=uploaded.size_bytes)


@router.post(
    "/change-password",
    response_model=DetailMessage,
    summary="Change account password",
)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DetailMessage:
    UserService(db).change_password(
        actor=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return DetailMessage(detail="Password updated successfully")


@router.get(
    "/me/completeness",
    response_model=UserCompletenessRead,
    summary="Get profile completeness",
    description="Returns completion percentage and completed/missing profile fields.",
)
def profile_completeness(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserCompletenessRead:
    payload = UserService(db).get_completeness(actor=current_user)
    return UserCompletenessRead(**payload)


@router.get("/{user_id}", response_model=UserPublicRead, summary="Get public user profile")
def get_public_profile(
    user_id: int,
    db: Session = Depends(get_db),
    _: User | None = Depends(get_optional_current_user),
) -> UserPublicRead:
    return UserService(db).get_public_profile(user_id=user_id)


@router.get("/{user_id}/listings", response_model=Page[ListingRead], summary="Get public user listings")
def list_public_user_listings(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User | None = Depends(get_optional_current_user),
) -> Page[ListingRead]:
    items, total = UserService(db).list_public_user_listings(user_id=user_id, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return Page(
        items=items,
        meta=PageMeta(page=page, page_size=page_size, total_items=total, total_pages=total_pages),
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Soft delete my account")
def delete_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    UserService(db).soft_delete_me(actor=current_user)
    return None

