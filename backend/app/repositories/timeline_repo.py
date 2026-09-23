import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TimelineEvent


class TimelineRepository:
    def __init__(self, db: Session, user_id: uuid.UUID | None = None):
        self.db = db
        self.user_id = user_id

    def list_for_product(self, product_id: uuid.UUID) -> list[TimelineEvent]:
        return (
            self.db.execute(
                select(TimelineEvent)
                .where(TimelineEvent.product_id == product_id)
                .order_by(TimelineEvent.event_date.asc(), TimelineEvent.created_at.asc())
            )
            .scalars()
            .all()
        )