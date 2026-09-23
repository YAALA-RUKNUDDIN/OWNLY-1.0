"""Datetime normalization helpers (SQLite vs PostgreSQL parity).

SQLite has no native timezone support and returns naive datetimes; PostgreSQL
with `DateTime(timezone=True)` returns offset-aware (UTC) values. Any comparison
between a value loaded from the database and a freshly computed one must
normalize first, otherwise Python raises:

    TypeError: can't compare offset-naive and offset-aware datetimes

Centralizing the rule here keeps every call site consistent (D-002/D-004).
"""
from __future__ import annotations

from datetime import datetime, timezone


def as_aware(dt: datetime | None) -> datetime | None:
    """Return `dt` as timezone-aware (naive values are treated as UTC)."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def utc_now() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)
