"""Ensure tests use a local SQLite DB unless DATABASE_URL is already set.

Avoids failures when developers have .env pointing at MySQL without latest migrations applied.
"""

from __future__ import annotations

import os

# Must run before `app` is imported by test modules.
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:///./pytest_marketplace.sqlite3"
