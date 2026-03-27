from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

BCRYPT_MAX_PASSWORD_BYTES = 72


def _assert_bcrypt_password_length(password: str) -> None:
    # bcrypt only uses first 72 bytes; we reject longer inputs to avoid surprises and runtime errors.
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("Password is too long for bcrypt (max 72 bytes)")


def hash_password(password: str) -> str:
    _assert_bcrypt_password_length(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    _assert_bcrypt_password_length(plain_password)
    return pwd_context.verify(plain_password, hashed_password)


def create_token(
    *,
    subject: str,
    token_type: Literal["access", "refresh", "reset"],
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    to_encode: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise ValueError("Invalid token") from e

