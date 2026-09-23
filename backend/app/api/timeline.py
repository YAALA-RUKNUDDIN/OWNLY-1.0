"""Product timeline endpoint."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import User
from app.repositories.product_repo import ProductRepository
from app.repositories.timeline_repo import TimelineRepository
from app.schemas.timeline import TimelineEventOut, TimelineResponse

router = APIRouter(tags=["timeline"])


@router.get("/products/{product_id}/timeline", response_model=TimelineResponse)
def product_timeline(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = ProductRepository(db, user.id).get(product_id)
    if not product:
        raise NotFoundError("Product not found.")
    events = TimelineRepository(db, user.id).list_for_product(product_id)
    return {"product_id": product_id, "events": events}