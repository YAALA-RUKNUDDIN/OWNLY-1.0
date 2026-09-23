"""Zero-setup local launcher for OWNLY.

Usage:
    python run_local.py            # start the API on http://localhost:8000
    python run_local.py --check    # verify imports + create tables, then exit

Sets SQLite database + local storage + no-op push automatically (no Docker,
no PostgreSQL, no Redis needed). Environment variables still override.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# Defaults BEFORE importing the app (pydantic-settings reads them at import).
os.environ.setdefault("DATABASE_URL", "sqlite:///./ownly_local.db")
os.environ.setdefault("JWT_SECRET", "local-dev-secret")
os.environ.setdefault("PUSH_PROVIDER", "noop")
os.environ.setdefault("STORAGE_PROVIDER", "local")
os.environ.setdefault("STORAGE_LOCAL_PATH", "./storage_data")
os.environ.setdefault("OCR_PROVIDER", "tesseract")

if "--check" in sys.argv:
    from app.core.database import Base, engine
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print(f"CHECK OK — dialect: {engine.dialect.name}, tables created.")
    sys.exit(0)

import uvicorn  # noqa: E402

if __name__ == "__main__":
    print("=" * 60)
    print("  OWNLY running at http://localhost:8000")
    print("  API docs:  http://localhost:8000/docs")
    print("  Data file: backend/ownly_local.db (SQLite)")
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, log_level="info")