"""Repair history and service record endpoints."""
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import (
    EventType, Product, Reminder, ReminderType, Repair, ServiceRecord, User,
)
from app.repositories.product_repo import ProductRepository
from app.services.timeline_service import record_event

router = APIRouter(tags=["repairs", "service"])


class RepairCreate(BaseModel):
    repair_date: date
    description: str = Field(min_length=1, max_length=2000)
    provider: str | None = Field(default=None, max_length=200)
    cost: float | None = Field(default=None, ge=0)
    notes: str | None = None


class RepairOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    product_id: uuid.UUID
    repair_date: date
    description: str
    provider: str | None
    cost: float | None
    notes: str | None


class ServiceRecordCreate(BaseModel):
    service_date: date
    next_service_date: date | None = None
    recurrence_months: int | None = Field(default=None, ge=1, le=60)
    provider: str | None = Field(default=None, max_length=200)
    cost: float | None = Field(default=None, ge=0)
    notes: str | None = None


class ServiceRecordOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    product_id: uuid.UUID
    service_date: date
    next_service_date: date | None
    provider: str | None
    cost: float | None
    notes: str | None


def _get_product(db: Session, user_id, product_id):
    product = ProductRepository(db, user_id).get(product_id)
    if not product:
        raise NotFoundError("Product not found.")
    return product


@router.post("/products/{product_id}/repairs", response_model=RepairOut, status_code=201)
def create_repair(
    product_id: uuid.UUID,
    body: RepairCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_product(db, user.id, product_id)
    repair = Repair(product_id=product_id, **body.model_dump())
    db.add(repair)
    db.flush()
    record_event(
        db, product_id, EventType.repair_recorded,
        title="Repair recorded",
        description=body.description[:200],
        event_date=body.repair_date,
        metadata={"cost": body.cost, "provider": body.provider},
    )
    db.commit()
    db.refresh(repair)
    return repair


@router.get("/products/{product_id}/repairs", response_model=list[RepairOut])
def list_repairs(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_product(db, user.id, product_id)
    return (
        db.execute(select(Repair).where(Repair.product_id == product_id).order_by(Repair.repair_date.desc()))
        .scalars()
        .all()
    )


@router.delete("/repairs/{repair_id}", status_code=204)
def delete_repair(
    repair_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repair = (
        db.execute(select(Repair).join(Repair.product).where(Repair.id == repair_id, Product.user_id == user.id))
        .scalar_one_or_none()
    )
    if not repair:
        raise NotFoundError("Repair not found.")
    db.delete(repair)
    db.commit()
    return None


@router.post("/products/{product_id}/service-records", response_model=ServiceRecordOut, status_code=201)
def create_service_record(
    product_id: uuid.UUID,
    body: ServiceRecordCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_product(db, user.id, product_id)
    next_date = body.next_service_date
    if next_date is None and body.recurrence_months:
        month = body.service_date.month - 1 + body.recurrence_months
        year = body.service_date.year + month // 12
        month = month % 12 + 1
        import calendar
        day = min(body.service_date.day, calendar.monthrange(year, month)[1])
        next_date = date(year, month, day)
    record = ServiceRecord(
        product_id=product_id,
        service_date=body.service_date,
        next_service_date=next_date,
        provider=body.provider,
        cost=body.cost,
        notes=body.notes,
    )
    db.add(record)
    db.flush()

    # Auto-create the next service reminder
    if next_date:
        db.add(Reminder(
            user_id=user.id,
            product_id=product_id,
            title="Service due",
            description=f"Scheduled service for {record.product.name if record.product else 'product'}",
            reminder_type=ReminderType.service_due,
            scheduled_date=next_date,
            recurrence_months=body.recurrence_months,
        ))
    record_event(
        db, product_id, EventType.service_completed,
        title="Service completed",
        description=body.provider or None,
        event_date=body.service_date,
        metadata={"cost": body.cost},
    )
    db.commit()
    db.refresh(record)
    return record


@router.get("/products/{product_id}/service-records", response_model=list[ServiceRecordOut])
def list_service_records(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_product(db, user.id, product_id)
    return (
        db.execute(
            select(ServiceRecord).where(ServiceRecord.product_id == product_id).order_by(ServiceRecord.service_date.desc())
        )
        .scalars()
        .all()
    )