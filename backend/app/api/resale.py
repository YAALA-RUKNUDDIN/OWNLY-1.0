"""Resale, Valuation, and Lifecycle Exit API endpoints."""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.resale import (
    PortfolioAnalyticsOut,
    ProductDisposeIn,
    ProductSellIn,
    ProductValuationOut,
    ResaleListingPacketOut,
)
from app.services.resale_service import ResaleService

router = APIRouter(tags=["resale"])


@router.get("/products/{product_id}/valuation", response_model=ProductValuationOut)
def get_product_valuation(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve estimated resale value, TCO, and depreciation metrics for a product."""
    service = ResaleService(db, current_user)
    return service.get_product_valuation(product_id)


@router.get("/products/{product_id}/resale-packet", response_model=ResaleListingPacketOut)
def get_resale_listing_packet(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate ready-to-paste marketplace listings (Markdown & Plain Text) with verified receipts."""
    service = ResaleService(db, current_user)
    return service.generate_resale_packet(product_id)


@router.post("/products/{product_id}/sell", response_model=ProductValuationOut)
def sell_product(
    product_id: uuid.UUID,
    body: ProductSellIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark product as sold, record selling price and notes, and compute realized net ownership cost."""
    service = ResaleService(db, current_user)
    return service.sell_product(product_id, body)


@router.post("/products/{product_id}/dispose", response_model=ProductValuationOut)
def dispose_product(
    product_id: uuid.UUID,
    body: ProductDisposeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark product as recycled, donated, or archived."""
    service = ResaleService(db, current_user)
    return service.dispose_product(product_id, body)


@router.patch("/products/{product_id}/condition", response_model=ProductValuationOut)
def update_product_condition(
    product_id: uuid.UUID,
    condition: str = Query(..., description="Condition: mint, excellent, good, fair, or poor"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update item condition and re-calculate estimated resale value."""
    service = ResaleService(db, current_user)
    return service.update_condition(product_id, condition)


@router.get("/portfolio/analytics", response_model=PortfolioAnalyticsOut)
def get_portfolio_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregated portfolio analytics: total value, current resale value, realized sales, and category breakdown."""
    service = ResaleService(db, current_user)
    return service.get_portfolio_analytics()
