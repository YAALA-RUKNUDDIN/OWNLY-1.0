"""Warranty and return-window business logic.

Status is always COMPUTED from dates — never stored stale:
  - active:        end_date in the future, more than 30 days away
  - expiring_soon: end_date in the future, within 30 days
  - expired:       end_date in the past
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from app.core.datetime_utils import as_aware

EXPIRING_SOON_DAYS = 30
RETURN_EXPIRING_SOON_DAYS = 5


def compute_warranty_status(end_date: datetime | date, today: date | None = None) -> tuple[str, int]:
    """Returns (status, days_remaining). days_remaining can be negative (expired)."""
    today = today or datetime.now().date()
    end = end_date.date() if isinstance(end_date, datetime) else end_date
    days = (end - today).days
    if days < 0:
        return "expired", days
    if days <= EXPIRING_SOON_DAYS:
        return "expiring_soon", days
    return "active", days


def compute_return_status(
    purchase_date: datetime | date,
    return_days: int,
    today: date | None = None,
) -> tuple[str, int | None, date | None]:
    """Returns (status, days_remaining, return_end_date)."""
    if not return_days or return_days <= 0:
        return "none", None, None
    today = today or datetime.now().date()
    start = purchase_date.date() if isinstance(purchase_date, datetime) else purchase_date
    end = start + timedelta(days=return_days)
    days = (end - today).days
    if days < 0:
        return "expired", days, end
    if days <= RETURN_EXPIRING_SOON_DAYS:
        return "expiring_soon", days, end
    return "active", days, end


def warranty_milestones(end_date: datetime | date, today: date | None = None) -> list[str]:
    """Which notification milestones apply today for this warranty end date."""
    today = today or datetime.now().date()
    end = end_date.date() if isinstance(end_date, datetime) else end_date
    days = (end - today).days
    if days == 0:
        return ["today"]
    if days == 1:
        return ["1d"]
    if days == 7:
        return ["7d"]
    if days == 30:
        return ["30d"]
    if days == 90:
        return ["90d"]
    return []


def resolve_end_date(start_date: datetime, end_date: datetime | None, duration_months: int | None) -> datetime:
    """Derive end_date from duration_months when not explicitly given.

    The returned value is timezone-aware (UTC) so persisted values behave
    identically on SQLite and PostgreSQL (see app/core/datetime_utils).
    """
    if end_date:
        return as_aware(end_date)
    if duration_months:
        month = start_date.month - 1 + duration_months
        year = start_date.year + month // 12
        month = month % 12 + 1
        day = min(start_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return as_aware(datetime(year, month, day))
    raise ValueError("Either end_date or duration_months is required")