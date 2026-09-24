"""Warranty Claim Assistant and Brand Support API endpoints."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import User
from app.schemas.claim import (
    BrandSupportOut,
    ClaimCreate,
    ClaimDossierOut,
    ClaimOut,
    ClaimUpdate,
)
from app.services.brand_support_service import BrandSupportService
from app.services.claim_service import ClaimService

router = APIRouter(tags=["claims"])


# 1. Brand Support Directory Endpoints
@router.get("/claims/support-directory", response_model=list[BrandSupportOut])
def list_brand_support_directory(
    category: Optional[str] = Query(None, description="Filter by product category"),
):
    """Retrieve official manufacturer support portals and hotlines from the directory."""
    brands = BrandSupportService.list_all_brands(category=category)
    return [
        BrandSupportOut(
            brand=b.brand,
            category=b.category,
            support_phone=b.support_phone,
            support_url=b.support_url,
            claim_portal_url=b.claim_portal_url,
            warranty_check_url=b.warranty_check_url,
            serial_lookup_url=b.serial_lookup_url,
            support_hours=b.support_hours,
            notes=b.notes,
        )
        for b in brands
    ]


@router.get("/claims/support-directory/{brand}", response_model=BrandSupportOut)
def get_brand_support(brand: str):
    """Look up official support phone and claim portal for a specific manufacturer."""
    info = BrandSupportService.get_brand_support(brand)
    if not info:
        raise NotFoundError(f"No curated support contacts found for brand '{brand}'.")
    return BrandSupportOut(
        brand=info.brand,
        category=info.category,
        support_phone=info.support_phone,
        support_url=info.support_url,
        claim_portal_url=info.claim_portal_url,
        warranty_check_url=info.warranty_check_url,
        serial_lookup_url=info.serial_lookup_url,
        support_hours=info.support_hours,
        notes=info.notes,
    )


# 2. Product-scoped Claim Endpoints
@router.post(
    "/products/{product_id}/claims",
    response_model=ClaimOut,
    status_code=status.HTTP_201_CREATED,
)
def file_warranty_claim(
    product_id: uuid.UUID,
    body: ClaimCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """File a new warranty claim for a product and append an event to its ownership timeline."""
    service = ClaimService(db, user)
    claim = service.file_claim(
        product_id=product_id,
        title=body.title,
        issue_description=body.issue_description,
        incident_date=body.incident_date,
        warranty_id=body.warranty_id,
        claim_reference=body.claim_reference,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
    )
    return service.format_claim_out(claim)


@router.get("/products/{product_id}/claims", response_model=list[ClaimOut])
def list_product_claims(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all warranty claims filed for a given product."""
    service = ClaimService(db, user)
    claims = service.claim_repo.list_for_product(product_id)
    return [service.format_claim_out(c) for c in claims]


# 3. User-level Claim Endpoints
@router.get("/claims", response_model=dict)
def list_user_claims(
    status: Optional[str] = Query(None, description="Filter by claim status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all claims accessible to the user across personal and household vaults."""
    service = ClaimService(db, user)
    claims, total = service.claim_repo.list_for_user(status=status, limit=limit, offset=offset)
    return {
        "items": [service.format_claim_out(c) for c in claims],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/claims/{claim_id}", response_model=ClaimOut)
def get_claim(
    claim_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch details and brand support contacts for a specific claim."""
    service = ClaimService(db, user)
    claim = service.claim_repo.get(claim_id)
    if not claim:
        raise NotFoundError("Claim not found.")
    return service.format_claim_out(claim)


@router.patch("/claims/{claim_id}", response_model=ClaimOut)
def update_claim(
    claim_id: uuid.UUID,
    body: ClaimUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update claim status, RMA reference, resolution notes, or costs covered."""
    service = ClaimService(db, user)
    updated = service.update_claim(
        claim_id=claim_id,
        **body.model_dump(exclude_unset=True),
    )
    return service.format_claim_out(updated)


@router.delete("/claims/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(
    claim_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete or withdraw a warranty claim."""
    service = ClaimService(db, user)
    service.delete_claim(claim_id)
    return None


@router.get("/claims/{claim_id}/dossier", response_model=ClaimDossierOut)
def get_claim_dossier(
    claim_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compile and generate the complete Claim Dossier packet with signed proof-of-purchase URLs."""
    service = ClaimService(db, user)
    return service.generate_dossier(claim_id)
