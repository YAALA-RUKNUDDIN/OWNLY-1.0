import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ClaimStatusLiteral = Literal[
    "draft", "submitted", "in_review", "approved", "repaired", "replaced", "rejected", "closed"
]


class BrandSupportOut(BaseModel):
    brand: str
    category: str
    support_phone: str
    support_url: str
    claim_portal_url: str
    warranty_check_url: Optional[str] = None
    serial_lookup_url: Optional[str] = None
    support_hours: str = "Mon-Fri 9am-6pm local time"
    notes: Optional[str] = None


class ClaimCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    issue_description: str = Field(min_length=1, max_length=5000)
    incident_date: datetime
    warranty_id: Optional[uuid.UUID] = None
    claim_reference: Optional[str] = Field(default=None, max_length=100)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)


class ClaimUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    issue_description: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    status: Optional[ClaimStatusLiteral] = None
    claim_reference: Optional[str] = Field(default=None, max_length=100)
    incident_date: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    claim_cost_covered: Optional[float] = None
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    product_brand: Optional[str] = None
    product_serial: Optional[str] = None
    warranty_id: Optional[uuid.UUID] = None
    warranty_provider: Optional[str] = None
    claim_reference: Optional[str] = None
    title: str
    issue_description: str
    status: ClaimStatusLiteral
    incident_date: datetime
    resolution_notes: Optional[str] = None
    claim_cost_covered: Optional[float] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    brand_support: Optional[BrandSupportOut] = None


class ClaimDossierOut(BaseModel):
    dossier_id: uuid.UUID
    generated_at: datetime
    claim: ClaimOut
    product: dict[str, Any]
    warranty: Optional[dict[str, Any]] = None
    documents: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    brand_support: Optional[BrandSupportOut] = None
    claimant: dict[str, Any]
    formatted_markdown: str
