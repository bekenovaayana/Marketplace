from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPair,
)
from app.schemas.user import DetailMessage
from app.schemas.user import UserRead, UserRegisterCreate
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterCreate, db: Session = Depends(get_db)) -> UserRead:
    try:
        user = AuthService(db).register(
            full_name=payload.full_name,
            email=str(payload.email),
            password=payload.password,
            preferred_language=payload.preferred_language,
        )
        return user
    except HTTPException:
        # Re-raise HTTPExceptions (e.g. 409 duplicate email) unchanged.
        raise
    except OperationalError as exc:
        logger.exception("Database connection error during register")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot connect to the database. Please try again later.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Database error during register")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred. Please try again later.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during register")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        ) from exc


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        tokens = AuthService(db).login(
            email=str(payload.email),
            password=payload.password,
            include_refresh=True,
        )
        tokens["token"] = tokens["access_token"]
        return TokenPair(**tokens)
    except HTTPException:
        raise
    except OperationalError as exc:
        logger.exception("Database connection error during login")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot connect to the database. Please try again later.",
        ) from exc
    except SQLAlchemyError as exc:
        logger.exception("Database error during login")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred. Please try again later.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during login")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        ) from exc


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    tokens = AuthService(db).refresh_access_token(refresh_token=payload.refresh_token)
    return TokenPair(**tokens)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    data = AuthService(db).forgot_password(email=str(payload.email))
    return ForgotPasswordResponse(**data)


@router.post("/reset-password", response_model=DetailMessage)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> DetailMessage:
    AuthService(db).reset_password(reset_token=payload.reset_token, new_password=payload.new_password)
    return DetailMessage(detail="Password reset successfully")
