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


def days_in_month(year: int, month: int) -> int:
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if leap else 28
    return [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]


def add_months(dt: datetime, months: int) -> datetime:
    """Add whole months, clamping the day to the target month's length
    (Jan 31 + 1 month → Feb 28/29). Timezone awareness is preserved."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, days_in_month(year, month))
    return dt.replace(year=year, month=month, day=day)

