from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.report import ReportReasonCode, ReportStatus, ReportTargetType
from app.schemas.common import BaseSchema, TimestampFields
from app.schemas.user import UserPublicRead


class ReportCreate(BaseSchema):
    target_type: ReportTargetType = Field(
        description="Target type. Allowed: listing, user",
        examples=[ReportTargetType.LISTING.value],
    )
    target_id: int = Field(gt=0, description="ID of the reported listing/user")
    reason_code: ReportReasonCode = Field(
        description=(
            "Reason code. Allowed: spam, fake_listing, scam, duplicate, "
            "offensive_content, prohibited_item, harassment, other"
        ),
        examples=[ReportReasonCode.SPAM.value],
    )
    reason_text: str | None = Field(default=None, max_length=1000, description="Optional details from reporter")


class ReportResolveRequest(BaseSchema):
    resolution_note: str | None = Field(default=None, max_length=2000)


class ReportRead(BaseSchema, TimestampFields):
    id: int
    reporter_user_id: int
    target_type: ReportTargetType
    target_id: int
    reason_code: ReportReasonCode
    reason_text: str | None
    status: ReportStatus
    resolution_note: str | None
    reviewed_by_admin_id: int | None
    reviewed_at: datetime | None
    reporter: UserPublicRead | None = None
    reviewed_by_admin: UserPublicRead | None = None
    target_preview: str | None = None
