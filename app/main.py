from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.api_router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import __all_models  # noqa: F401
from app.web.admin import router as admin_router

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

# Allow any localhost / 127.0.0.1 origin regardless of port.
# The regex covers both http and https and any port number so that
# the Flutter web dev server (random high port) is always accepted.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET,
    same_site="lax",
    https_only=settings.ENV != "local",
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors: list[dict] = []
    for err in exc.errors():
        loc = err.get("loc") or ()
        field = None
        if isinstance(loc, (list, tuple)):
            # Typically: ("body","field") or ("query","field")
            field = ".".join(str(p) for p in loc[1:]) if len(loc) > 1 else str(loc[0]) if loc else None
        errors.append(
            {
                "field": field,
                "message": err.get("msg", "Invalid value"),
            }
        )
    return JSONResponse(status_code=422, content={"errors": errors})


app.include_router(api_router)
app.include_router(admin_router)


@app.on_event("startup")
def _auto_create_db_for_local_sqlite() -> None:
    if settings.ENV != "local" or not settings.AUTO_CREATE_DB:
        return
    if not settings.sqlalchemy_database_uri.startswith("sqlite"):
        return
    Base.metadata.create_all(bind=engine)

uploads_path = Path(settings.UPLOADS_DIR)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount(settings.UPLOADS_URL_PREFIX, StaticFiles(directory=str(uploads_path)), name="uploads")
