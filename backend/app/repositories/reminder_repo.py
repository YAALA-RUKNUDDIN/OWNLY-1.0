import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Reminder


class ReminderRepository:
    def __init__(self, db: Session, user_id: uuid.UUID | None = None):
        self.db = db
        self.user_id = user_id

    def list_for_user(
        self,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[Reminder]:
        q = select(Reminder).where(Reminder.user_id == self.user_id)
        if status:
            q = q.where(Reminder.status == status)
        if from_date:
            q = q.where(Reminder.scheduled_date >= from_date)
        if to_date:
            q = q.where(Reminder.scheduled_date <= to_date)
        return self.db.execute(q.order_by(Reminder.scheduled_date.asc())).scalars().all()

    def get(self, reminder_id: uuid.UUID) -> Reminder | None:
        return (
            self.db.execute(select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == self.user_id))
            .scalar_one_or_none()
        )