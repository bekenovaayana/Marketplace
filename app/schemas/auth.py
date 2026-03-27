from __future__ import annotations

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenPair(BaseSchema):
    access_token: str
    token: str | None = Field(default=None, description="Legacy alias for access_token")
    token_type: str = "bearer"
    refresh_token: str | None = None


class TokenPayload(BaseSchema):
    sub: str
    type: str


class RefreshRequest(BaseSchema):
    refresh_token: str


class ForgotPasswordRequest(BaseSchema):
    email: EmailStr


class ForgotPasswordResponse(BaseSchema):
    reset_token: str | None = None
    detail: str


class ResetPasswordRequest(BaseSchema):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)

