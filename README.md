# Marketplace Backend (FastAPI)

Production-style backend scaffold for a marketplace MVP (FastAPI + SQLAlchemy + MySQL) using strict layered architecture:

- `app/core`: config, security, dependencies
- `app/db`: engine/session/base
- `app/models`: SQLAlchemy ORM models
- `app/schemas`: Pydantic schemas
- `app/repositories`: DB access layer (CRUD)
- `app/services`: business logic
- `app/api`: routers (no business logic)
- `app/utils`: helpers

## Local setup

1. Create a virtualenv, install deps:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Create `.env` from `.env.example` and fill values.

3. Run:

```bash
uvicorn app.main:app --reload
```

Open Swagger UI at `/docs`.
