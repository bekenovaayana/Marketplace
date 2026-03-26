from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_token, hash_password, verify_password
from app.core.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, *, full_name: str, email: str, password: str, preferred_language: str | None = None) -> User:
        user = User(
            full_name=full_name,
            email=email.lower(),
            password_hash=hash_password(password),
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
        if not user or not verify_password(password, user.password_hash):
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

