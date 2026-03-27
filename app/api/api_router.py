from __future__ import annotations

from fastapi import APIRouter

from app.api import attachments, auth, categories, chats, conversations, favorites, home, listings, messages, meta, notifications, payments, promotions, reports, uploads, users


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(home.router)
api_router.include_router(listings.router)
api_router.include_router(favorites.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(chats.router)
api_router.include_router(notifications.router)
api_router.include_router(payments.router)
api_router.include_router(promotions.router)
api_router.include_router(meta.router)
api_router.include_router(uploads.router)
api_router.include_router(attachments.router)
api_router.include_router(reports.router)

