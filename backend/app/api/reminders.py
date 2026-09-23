"""Reminder CRUD endpoints."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import NotFoundError, ValidationError
from app.models import EventType, Product, Reminder, ReminderStatus, ReminderType, User
from app.repositories.product_repo import ProductRepository
from app.repositories.reminder_repo import ReminderRepository
from app.schemas.reminder import ReminderCreate, ReminderOut, ReminderUpdate
from app.services.timeline_service import record_event

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
def list_reminders(
    status: str | None = Query(None, pattern="^(upcoming|completed|dismissed)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ReminderRepository(db, user.id).list_for_user(status=status)


@router.post("", response_model=ReminderOut, status_code=201)
def create_reminder(
    body: ReminderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.product_id:
        product = ProductRepository(db, user.id).get(body.product_id)
        if not product:
            raise NotFoundError("Product not found.")
    reminder = Reminder(user_id=user.id, **body.model_dump())
    db.add(reminder)
    db.flush()
    if reminder.product_id:
        record_event(
            db, reminder.product_id, EventType.reminder_created,
            title=f"Reminder set: {reminder.title}",
            event_date=reminder.scheduled_date,
        )
    db.commit()
    db.refresh(reminder)
    return reminder


@router.patch("/{reminder_id}", response_model=ReminderOut)
def update_reminder(
    reminder_id: uuid.UUID,
    body: ReminderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = ReminderRepository(db, user.id).get(reminder_id)
    if not reminder:
        raise NotFoundError("Reminder not found.")
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(reminder, field, value)
    db.add(reminder)
    if changes.get("status") == "completed":
        record_event(
            db, reminder.product_id, EventType.reminder_completed,
            title=f"Reminder completed: {reminder.title}",
        ) if reminder.product_id else None
    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(
    reminder_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = ReminderRepository(db, user.id).get(reminder_id)
    if not reminder:
        raise NotFoundError("Reminder not found.")
    db.delete(reminder)
    db.commit()
    return None