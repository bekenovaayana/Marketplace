from __future__ import annotations

from app.schemas.common import BaseSchema


class UploadedImageRead(BaseSchema):
    url: str
    content_type: str
    size_bytes: int
