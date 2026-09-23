"""Records timeline events for every meaningful ownership action."""
from datetime import date

from sqlalchemy.orm import Session

from app.models import EventType, TimelineEvent


def record_event(
    db: Session,
    product_id,
    event_type: EventType,
    title: str,
    description: str | None = None,
    event_date: date | None = None,
    metadata: dict | None = None,
) -> TimelineEvent:
    event = TimelineEvent(
        product_id=product_id,
        event_type=event_type,
        title=title,
        description=description,
        event_date=event_date or date.today(),
        metadata_json=metadata,
    )
    db.add(event)
    db.flush()
    return event