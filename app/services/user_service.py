from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.listing import ListingStatus
from app.models.user import UserStatus
from app.repositories.listing_repository import ListingRepository
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.listings = ListingRepository(db)

    def update_me(self, *, actor: User, data: dict) -> User:
        def field_error(field: str, message: str) -> HTTPException:
            return HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"errors": [{"field": field, "message": message}]},
            )

        kg_phone_re = re.compile(r"^\+996\d{9}$")

        if "first_name" in data and data["first_name"] is not None:
            data["first_name"] = data["first_name"].strip()
            if data["first_name"] == "":
                raise field_error("first_name", "cannot be empty")
        if "last_name" in data and data["last_name"] is not None:
            data["last_name"] = data["last_name"].strip()
            if data["last_name"] == "":
                raise field_error("last_name", "cannot be empty")

        # If client updates first/last without providing full_name, keep full_name in sync.
        if "full_name" not in data and ("first_name" in data or "last_name" in data):
            first = data.get("first_name", actor.first_name) or ""
            last = data.get("last_name", actor.last_name) or ""
            computed = " ".join([p for p in [first.strip(), last.strip()] if p])
            if computed:
                data["full_name"] = computed

        if "full_name" in data and data["full_name"] is not None:
            normalized = " ".join(data["full_name"].strip().split())
            if not normalized:
                raise field_error("full_name", "cannot be empty")
            data["full_name"] = normalized

        if "bio" in data and isinstance(data["bio"], str):
            data["bio"] = data["bio"].strip()
        if "city" in data and isinstance(data["city"], str):
            data["city"] = data["city"].strip()

        if "preferred_language" in data and data["preferred_language"] is not None:
            normalized_lang = str(data["preferred_language"]).strip().lower()
            if normalized_lang not in ("en", "ru"):
                raise field_error("preferred_language", "must be 'en' or 'ru'")
            data["preferred_language"] = normalized_lang

        if "phone" in data and data["phone"] is not None:
            normalized_phone = str(data["phone"]).strip().replace(" ", "")
            if not kg_phone_re.match(normalized_phone):
                raise field_error("phone", "must match +996XXXXXXXXX (9 digits after +996)")
            data["phone"] = normalized_phone

        try:
            updated = self.users.update(actor, data)
            self.db.commit()
            return updated
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict")

    def set_avatar(self, *, actor: User, avatar_url: str) -> User:
        updated = self.users.update(actor, {"avatar_url": avatar_url})
        self.db.commit()
        return updated

    def change_password(self, *, actor: User, current_password: str, new_password: str) -> None:
        if new_password == current_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="new_password must be different from current_password",
            )
        if not verify_password(current_password, actor.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

        self.users.update(actor, {"password_hash": hash_password(new_password)})
        self.db.commit()

    def get_completeness(self, *, actor: User) -> dict:
        checks = {
            "full_name": bool(actor.full_name and actor.full_name.strip()),
            "phone": bool(actor.phone and actor.phone.strip()),
            "city": bool(actor.city and actor.city.strip()),
            "bio": bool(actor.bio and actor.bio.strip()),
            "avatar_url": bool(actor.avatar_url and actor.avatar_url.strip()),
            "email_verified": bool(actor.email_verified),
            "phone_verified": bool(actor.phone_verified),
        }
        completed_fields = [name for name, ok in checks.items() if ok]
        missing_fields = [name for name, ok in checks.items() if not ok]
        percentage = int(round((len(completed_fields) / len(checks)) * 100)) if checks else 0
        return {
            "percentage": percentage,
            "completed_fields": completed_fields,
            "missing_fields": missing_fields,
        }

    def get_public_profile(self, *, user_id: int) -> User:
        user = self.users.get_by_id(user_id)
        if not user or user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.active_listings_count = self.listings.count_active_by_owner(owner_id=user.id)
        return user

    def list_public_user_listings(self, *, user_id: int, page: int, page_size: int) -> tuple[list, int]:
        user = self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return self.listings.list_by_owner(
            owner_id=user_id,
            status=ListingStatus.ACTIVE,
            page=page,
            page_size=page_size,
            with_owner=True,
        )

    def soft_delete_me(self, *, actor: User) -> None:
        if actor.status == UserStatus.DELETED:
            return
        self.users.update(actor, {"status": UserStatus.DELETED})
        self.db.commit()
