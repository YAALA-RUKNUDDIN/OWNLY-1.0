"""Database engine and session management.

Supports two modes via DATABASE_URL:
  - SQLite (local dev, zero setup):  sqlite:///./ownly_local.db
  - PostgreSQL (production):         postgresql+psycopg2://user:pass@host/db

Public API consumed across the app (contract — do not change without
auditing import sites):
  - Base          declarative base shared by every model
  - engine        SQLAlchemy Engine
  - SessionLocal  session factory
  - get_db        FastAPI dependency yielding a session
  - GUID          dialect-agnostic UUID column type (PG native UUID / CHAR(36))
"""
import uuid

from sqlalchemy import CHAR, MetaData, create_engine
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

# Explicit constraint names keep future Alembic autogenerate diffs stable
# (anonymous constraints cannot be dropped/altered reliably).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    PostgreSQL → native UUID (indexable, compact).
    Everything else (SQLite dev/test) → CHAR(36).
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _build_engine():
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        # SQLite (dev/test): allow the session to be shared across
        # FastAPI's threadpool threads.
        return create_engine(url, connect_args={"check_same_thread": False})
    # PostgreSQL (production): pre-ping drops connections killed by the
    # server or an intermediate LB instead of surfacing them as 500s.
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


engine = _build_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
