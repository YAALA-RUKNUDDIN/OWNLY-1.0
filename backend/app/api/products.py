"""Product CRUD, search, filters, pagination. All queries user-scoped and household-aware."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_current_user
from app.core.analytics_events import AnalyticsEvent
from app.core.database import get_db
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.integrations.analytics import track
from app.models import EventType, Product, ProductStatus, User
from app.repositories.product_repo import ProductRepository
from app.schemas.household import ProductShareRequest
from app.schemas.product import ProductCreate, ProductListOut, ProductOut, ProductUpdate
from app.services.household_service import HouseholdService
from app.services.subscription_service import enforce_product_quota
from app.services.timeline_service import record_event
from app.services.warranty_service import compute_return_status, compute_warranty_status

router = APIRouter(prefix="/products", tags=["products"])


def _serialize(db: Session, p: Product) -> dict:
    data = ProductOut.model_validate(p).model_dump(mode="json")
    data["household_id"] = str(p.household_id) if p.household_id else None
    data["is_shared"] = p.household_id is not None
    warranty = next(iter(p.warranties), None) if p.warranties else None
    if warranty:
        status, days = compute_warranty_status(warranty.end_date)
        data["warranty"] = {"status": status, "days_remaining": days, "end_date": warranty.end_date.isoformat()}
    else:
        data["warranty"] = {"status": "none", "days_remaining": None, "end_date": None}
    r_status, r_days, r_end = compute_return_status(p.purchase_date, p.return_days)
    data["return_window"] = {
        "tracked": p.return_days > 0,
        "status": r_status,
        "days_remaining": r_days,
        "end_date": r_end.isoformat() if r_end else None,
    }
    return data


@router.get("", response_model=ProductListOut)
def list_products(
    search: str | None = None,
    category: str | None = None,
    status: str | None = None,
    warranty_status: str | None = Query(None, pattern="^(expiring|valid|expired|none)$"),
    purchase_year: int | None = Query(None, ge=1900, le=2100),
    scope: str = Query("all", pattern="^(all|personal|household)$"),
    household_id: uuid.UUID | None = None,
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if status and status not in ProductStatus.__members__:
        raise ValidationError("Invalid product status.", {"fields": {"status": "unknown status"}})
    repo = ProductRepository(db, user.id)
    products, total = repo.list(
        search=search, category=category, status=status,
        warranty_status=warranty_status, purchase_year=purchase_year,
        scope=scope, household_id=household_id,
        page=pagination.page, page_size=pagination.page_size,
    )
    return {
        "items": [_serialize(db, p) for p in products],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    body: ProductCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.category not in [
        "smartphones", "laptops", "tablets", "headphones", "electronics",
        "home_appliances", "furniture", "vehicles", "watches", "cameras",
        "gaming", "other",
    ]:
        raise ValidationError("Unknown category.", {"fields": {"category": f"must be one of the supported categories"}})
    enforce_product_quota(db, user)
    repo = ProductRepository(db, user.id)
    product = repo.create(**body.model_dump())
    record_event(
        db, product.id, EventType.product_added,
        title="Product added",
        description=f"{product.name} added to your vault",
        event_date=product.purchase_date.date() if isinstance(product.purchase_date, datetime) else product.purchase_date,
    )
    db.commit()
    db.refresh(product)
    track(AnalyticsEvent.product_added, user.id, {"category": product.category})
    return _serialize(db, product)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = ProductRepository(db, user.id).get_with_documents(product_id)
    if not product:
        raise NotFoundError("Product not found.")
    return _serialize(db, product)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ProductRepository(db, user.id)
    product = repo.get(product_id)
    if not product:
        raise NotFoundError("Product not found.")
    if not repo.can_edit_product(product):
        raise ForbiddenError("You have read-only access to this product.")

    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    old_status = product.status
    for field, value in changes.items():
        setattr(product, field, value)
    db.add(product)
    if changes.get("status") == "sold" and old_status != ProductStatus.sold:
        record_event(db, product_id, EventType.product_sold, title="Product sold")
    elif changes.get("status") == "archived" and old_status != ProductStatus.archived:
        record_event(db, product_id, EventType.product_archived, title="Product archived")
    else:
        record_event(db, product_id, EventType.product_updated, title="Product details updated")
    db.commit()
    db.refresh(product)
    return _serialize(db, product)


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ProductRepository(db, user.id)
    product = repo.get(product_id)
    if not product:
        raise NotFoundError("Product not found.")
    if not repo.can_edit_product(product):
        raise ForbiddenError("You have read-only access to this product.")

    repo.soft_delete(product)
    db.commit()
    track(AnalyticsEvent.product_deleted, user.id)
    return None


@router.post("/{product_id}/share", response_model=ProductOut)
def share_product(
    product_id: uuid.UUID,
    body: ProductShareRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HouseholdService(db)
    product = service.share_product(product_id, user.id, body.household_id)
    return _serialize(db, product)