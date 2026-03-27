from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.core.config import settings
from app.models.user import User, UserStatus
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, *, full_name: str, email: str, password: str, preferred_language: str | None = None) -> User:
        try:
            password_hash = hash_password(password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        user = User(
            full_name=full_name,
            email=email.lower(),
            password_hash=password_hash,
            preferred_language=preferred_language,
        )
        try:
            self.users.create(user)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        return user

    def login(self, *, email: str, password: str, include_refresh: bool = True) -> dict:
        user = self.users.get_by_email(email.lower())
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
        try:
            ok = verify_password(password, user.password_hash)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        if not ok:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        access = create_token(
            subject=str(user.id),
            token_type="access",
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh = None
        if include_refresh:
            refresh = create_token(
                subject=str(user.id),
                token_type="refresh",
                expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )

        return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

    def refresh_access_token(self, *, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
        user = self.users.get_by_id(int(user_id))
        if not user or user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

        access = create_token(
            subject=str(user.id),
            token_type="access",
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return {"access_token": access, "token_type": "bearer"}

    def forgot_password(self, *, email: str) -> dict:
        user = self.users.get_by_email(email.lower())
        reset_token: str | None = None
        if user:
            reset_token = create_token(
                subject=str(user.id),
                token_type="reset",
                expires_delta=timedelta(hours=1),
            )
        return {"reset_token": reset_token, "detail": "Reset token generated"}

    def reset_password(self, *, reset_token: str, new_password: str) -> None:
        if len(new_password) < 8:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters")
        try:
            payload = decode_token(reset_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
        if payload.get("type") != "reset":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
        user = self.users.get_by_id(int(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
        self.users.update(user, {"password_hash": hash_password(new_password)})
        self.db.commit()

