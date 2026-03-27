from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserStatus
from app.repositories.user_repository import UserRepository


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _resolve_user_from_token(*, db: Session, token: str) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    try:
        payload = decode_token(token)
    except ValueError:
        raise unauthorized

    if payload.get("type") != "access":
        raise unauthorized

    user_id = payload.get("sub")
    if not user_id:
        raise unauthorized

    user = UserRepository(db).get_by_id(int(user_id))
    if not user or user.status != UserStatus.ACTIVE:
        raise unauthorized
    return user


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    return _resolve_user_from_token(db=db, token=token)


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def get_optional_current_user(
    db: Session = Depends(get_db),
    token: str | None = Depends(optional_oauth2_scheme),
) -> User | None:
    if not token:
        return None
    return _resolve_user_from_token(db=db, token=token)

