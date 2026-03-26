from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenPair
from app.schemas.user import UserRead, UserRegisterCreate
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterCreate, db: Session = Depends(get_db)) -> UserRead:
    user = AuthService(db).register(
        full_name=payload.full_name,
        email=str(payload.email),
        password=payload.password,
        preferred_language=payload.preferred_language,
    )
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    tokens = AuthService(db).login(email=str(payload.email), password=payload.password, include_refresh=True)
    return TokenPair(**tokens)

