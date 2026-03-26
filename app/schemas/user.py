from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field

from app.models.user import UserStatus
from app.schemas.common import BaseSchema, TimestampFields


class UserRegisterCreate(BaseSchema):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    preferred_language: str | None = Field(default=None, max_length=10)


class UserUpdate(BaseSchema):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    bio: str | None = None
    city: str | None = Field(default=None, max_length=120)
    preferred_language: str | None = Field(default=None, max_length=10)


class UserRead(BaseSchema, TimestampFields):
    id: int
    full_name: str
    email: EmailStr
    bio: str | None
    city: str | None
    preferred_language: str | None
    status: UserStatus
    last_seen_at: datetime | None


class UserPublicRead(BaseSchema, TimestampFields):
    id: int
    full_name: str
    city: str | None

