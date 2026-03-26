from __future__ import annotations

from fastapi import APIRouter

from app.api import auth, conversations, favorites, listings, messages, payments, promotions, users


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(listings.router)
api_router.include_router(favorites.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(payments.router)
api_router.include_router(promotions.router)

