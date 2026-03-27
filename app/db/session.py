from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.models import __all_models  # noqa: F401


connect_args = {}
if settings.sqlalchemy_database_uri.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.sqlalchemy_database_uri, pool_pre_ping=True, pool_recycle=3600, connect_args=connect_args)

if settings.ENV == "local" and settings.AUTO_CREATE_DB and settings.sqlalchemy_database_uri.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

