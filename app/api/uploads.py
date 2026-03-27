from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.upload import UploadedImageRead
from app.services.upload_service import UploadService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/images", response_model=UploadedImageRead)
def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> UploadedImageRead:
    _ = current_user
    return UploadService().upload_listing_image(upload_file=file)
