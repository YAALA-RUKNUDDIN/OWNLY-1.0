"""Subscription request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import PlanTier


class SubscriptionLimits(BaseModel):
    max_products: int | None  # None = unlimited
    features: list[str]


class SubscriptionUsage(BaseModel):
    products: int


class SubscriptionOut(BaseModel):
    tier: PlanTier
    status: str
    provider: str
    started_at: datetime | None = None
    expires_at: datetime | None = None
    canceled_at: datetime | None = None
    limits: SubscriptionLimits
    usage: SubscriptionUsage


class ActivateRequest(BaseModel):
    months: int = Field(default=12, ge=0, le=120,
                        description="Entitlement length; 0 = non-expiring grant.")
    provider_ref: str | None = Field(default=None, max_length=255)
