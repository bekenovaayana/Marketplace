from __future__ import annotations

from datetime import datetime
import re

from pydantic import EmailStr, Field, field_validator

from app.models.user import UserStatus, UserTheme
from app.schemas.common import BaseSchema, TimestampFields


_LANG_RE = re.compile(r"^(en|ru)$")
_THEME_RE = re.compile(r"^(light|dark|system)$")
_KG_PHONE_RE = re.compile(r"^\+996\d{9}$")


class UserRegisterCreate(BaseSchema):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    preferred_language: str | None = Field(default=None, max_length=10)

    @field_validator("full_name")
    @classmethod
    def _normalize_full_name(cls, v: str) -> str:
        normalized = " ".join(v.strip().split())
        if not normalized:
            raise ValueError("full_name cannot be empty")
        return normalized

    @field_validator("preferred_language")
    @classmethod
    def _validate_preferred_language(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = v.strip().lower()
        if not _LANG_RE.match(normalized):
            raise ValueError("preferred_language must be 'en' or 'ru'")
        return normalized


class UserUpdate(BaseSchema):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    full_name: str | None = Field(default=None, min_length=2, max_length=200, description="User display name")
    bio: str | None = Field(default=None, description="Public profile bio")
    city: str | None = Field(default=None, max_length=120, description="Current city")
    preferred_language: str | None = Field(default=None, max_length=10, description="Preferred language code")
    phone: str | None = Field(
        default=None,
        min_length=6,
        max_length=32,
        description="Kyrgyzstan phone number in E.164 format: +996XXXXXXXXX",
        examples=["+996500123456"],
    )
    theme: str | None = Field(default=None, max_length=16, description="UI theme: light, dark, or system")
    notify_new_message: bool | None = Field(default=None, description="In-app notifications for new chat messages")
    notify_contact_request: bool | None = Field(
        default=None, description="In-app notifications when someone requests contact on your listing"
    )
    notify_listing_favorited: bool | None = Field(
        default=None, description="In-app notifications when someone favorites your listing"
    )

    @field_validator("first_name", "last_name", "bio", "city", "full_name", mode="before")
    @classmethod
    def _trim_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("full_name")
    @classmethod
    def _normalize_full_name_update(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = " ".join(v.strip().split())
        if not normalized:
            raise ValueError("full_name cannot be empty")
        return normalized

    @field_validator("preferred_language")
    @classmethod
    def _validate_preferred_language_update(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = v.strip().lower()
        if not _LANG_RE.match(normalized):
            raise ValueError("preferred_language must be 'en' or 'ru'")
        return normalized

    @field_validator("phone")
    @classmethod
    def _validate_kg_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = v.strip().replace(" ", "")
        if not _KG_PHONE_RE.match(normalized):
            raise ValueError("phone must match +996XXXXXXXXX (9 digits after +996)")
        return normalized

    @field_validator("theme")
    @classmethod
    def _validate_theme(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = v.strip().lower()
        if not _THEME_RE.match(normalized):
            raise ValueError("theme must be 'light', 'dark', or 'system'")
        return normalized


class UserRead(BaseSchema, TimestampFields):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    full_name: str
    email: EmailStr
    bio: str | None
    city: str | None
    preferred_language: str | None
    theme: str = Field(default=UserTheme.SYSTEM.value)
    notify_new_message: bool = True
    notify_contact_request: bool = True
    notify_listing_favorited: bool = True
    phone: str | None
    avatar_url: str | None
    email_verified: bool
    phone_verified: bool
    is_admin: bool = False
    profile_completed: bool
    trust_score: int = Field(ge=0, le=100)
    status: UserStatus
    last_seen_at: datetime | None


class ChangePasswordRequest(BaseSchema):
    current_password: str = Field(min_length=1, max_length=128, description="Current account password")
    new_password: str = Field(min_length=8, max_length=128, description="New password (min 8 chars)")


class DetailMessage(BaseSchema):
    detail: str


class AvatarUploadResponse(BaseSchema):
    avatar_url: str = Field(description="Public avatar URL/path")
    content_type: str = Field(description="Uploaded file MIME type")
    size_bytes: int = Field(ge=0, description="Uploaded file size in bytes")


class UserPublicRead(BaseSchema, TimestampFields):
    id: int
    full_name: str
    city: str | None
    avatar_url: str | None
    bio: str | None
    active_listings_count: int = 0
    profile_completed: bool = False
    trust_score: int = Field(default=0, ge=0, le=100)


class UserCompletenessRead(BaseSchema):
    percentage: int = Field(ge=0, le=100)
    completed_fields: list[str]
    missing_fields: list[str]

