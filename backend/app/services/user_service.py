"""User-related services: default notification prefs, profile, export,
account deletion."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NotificationCategory, NotificationPreference, User

DEFAULT_LEAD_DAYS = [90, 30, 7, 1, 0]


def ensure_default_prefs(db: Session, user_id: uuid.UUID) -> None:
    existing = db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    if existing:
        return
    for category in NotificationCategory:
        db.add(NotificationPreference(
            user_id=user_id,
            category=category,
            enabled=True,
            lead_days=str(DEFAULT_LEAD_DAYS),
        ))
    db.flush()


def get_prefs(db: Session, user_id: uuid.UUID) -> list[NotificationPreference]:
    return (
        db.execute(
            select(NotificationPreference)
            .where(NotificationPreference.user_id == user_id)
            .order_by(NotificationPreference.category)
        )
        .scalars()
        .all()
    )


def parse_lead_days(raw: str) -> list[int]:
    try:
        import json
        return [int(d) for d in json.loads(raw)]
    except Exception:
        return list(DEFAULT_LEAD_DAYS)