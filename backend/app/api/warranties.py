"""Warranty management endpoints."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.datetime_utils import as_aware
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models import EventType, Product, User, Warranty
from app.repositories.product_repo import ProductRepository
from app.schemas.warranty import WarrantyCreate, WarrantyOut, WarrantyUpdate
from app.services.timeline_service import record_event
from app.services.warranty_service import compute_warranty_status, resolve_end_date

router = APIRouter(tags=["warranties"])


def _serialize(w: Warranty) -> dict:
    status, days = compute_warranty_status(w.end_date)
    data = WarrantyOut.model_validate(w).model_dump(mode="json")
    data["status"] = status
    data["days_remaining"] = days
    return data


@router.post("/products/{product_id}/warranty", response_model=WarrantyOut, status_code=201)
def create_warranty(
    product_id: uuid.UUID,
    body: WarrantyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = ProductRepository(db, user.id).get(product_id)
    if not product:
        raise NotFoundError("Product not found.")
    existing = db.scalar(select(Warranty).where(Warranty.product_id == product_id))
    if existing:
        raise ConflictError("This product already has a warranty. Use PATCH to update or extend it.")

    try:
        end_date = resolve_end_date(body.start_date, body.end_date, body.duration_months)
    except ValueError as e:
        raise ValidationError(str(e))
    if as_aware(end_date) <= as_aware(body.start_date):
        raise ValidationError("Warranty end date must be after the start date.")

    warranty = Warranty(
        product_id=product_id,
        provider=body.provider,
        warranty_type=body.warranty_type,
        start_date=body.start_date,
        end_date=end_date,
        duration_months=body.duration_months,
        notes=body.notes,
    )
    db.add(warranty)
    db.flush()
    record_event(
        db, product_id, EventType.warranty_started,
        title="Warranty started",
        description=f"{body.warranty_type.replace('_', ' ').title()} warranty until {end_date.date().isoformat()}",
        event_date=body.start_date.date(),
    )
    db.commit()
    db.refresh(warranty)
    return _serialize(warranty)


@router.get("/products/{product_id}/warranty", response_model=WarrantyOut | None)
def get_warranty(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = ProductRepository(db, user.id).get(product_id)
    if not product:
        raise NotFoundError("Product not found.")
    warranty = db.scalar(select(Warranty).where(Warranty.product_id == product_id))
    return _serialize(warranty) if warranty else None


@router.patch("/warranties/{warranty_id}", response_model=WarrantyOut)
def update_warranty(
    warranty_id: uuid.UUID,
    body: WarrantyUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    warranty = (
        db.execute(
            select(Warranty).join(Warranty.product).where(
                Warranty.id == warranty_id, Product.user_id == user.id
            )
        )
        .scalar_one_or_none()
    )
    if not warranty:
        raise NotFoundError("Warranty not found.")

    old_end = warranty.end_date
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(warranty, field, value)
    if body.end_date or body.duration_months:
        try:
            warranty.end_date = resolve_end_date(warranty.start_date, body.end_date, body.duration_months)
        except ValueError as e:
            raise ValidationError(str(e))
    if as_aware(warranty.end_date) <= as_aware(warranty.start_date):
        raise ValidationError("Warranty end date must be after the start date.")
    db.add(warranty)

    if as_aware(warranty.end_date) > as_aware(old_end):
        record_event(
            db, warranty.product_id, EventType.warranty_extended,
            title="Warranty extended",
            description=f"New expiry: {warranty.end_date.date().isoformat()}",
        )
    db.commit()
    db.refresh(warranty)
    return _serialize(warranty)


@router.delete("/warranties/{warranty_id}", status_code=204)
def delete_warranty(
    warranty_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    warranty = (
        db.execute(
            select(Warranty).join(Warranty.product).where(
                Warranty.id == warranty_id, Product.user_id == user.id
            )
        )
        .scalar_one_or_none()
    )
    if not warranty:
        raise NotFoundError("Warranty not found.")
    db.delete(warranty)
    db.commit()
    return None