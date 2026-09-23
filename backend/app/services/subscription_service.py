"""Plan entitlements and quota enforcement.

Single source of truth for "what is the user allowed to do": the API layer
asks this service, never the other way round. Entitlement is computed at
read time from (tier, status, expires_at) so an elapsed premium period
degrades to free automatically.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_utils import add_months, as_aware, utc_now
from app.core.errors import PlanLimitError
from app.models import PlanTier, Product, Subscription, SubscriptionStatus, User

FREE_FEATURES: tuple[str, ...] = ("basic_insights",)
PREMIUM_FEATURES: tuple[str, ...] = ("unlimited_products", "advanced_insights", "priority_support")


@dataclass(frozen=True)
class PlanLimits:
    max_products: int | None  # None = unlimited
    features: tuple[str, ...]


def limits_for(tier: PlanTier) -> PlanLimits:
    if tier == PlanTier.premium:
        return PlanLimits(max_products=None, features=PREMIUM_FEATURES)
    return PlanLimits(max_products=settings.FREE_PRODUCT_LIMIT, features=FREE_FEATURES)


def get_or_create(db: Session, user_id: uuid.UUID) -> Subscription:
    """Lazily materialize the free subscription so pre-existing accounts work
    without a data migration."""
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user_id))
    if sub is not None:
        return sub
    sub = Subscription(
        user_id=user_id,
        tier=PlanTier.free,
        status=SubscriptionStatus.active,
        provider="none",
    )
    db.add(sub)
    db.flush()
    return sub


def effective_tier(sub: Subscription, now: datetime | None = None) -> PlanTier:
    """Premium only while entitled; otherwise free."""
    if sub.tier != PlanTier.premium or sub.status == SubscriptionStatus.expired:
        return PlanTier.free
    expires_at = as_aware(sub.expires_at)
    if expires_at is not None and expires_at <= as_aware(now or utc_now()):
        return PlanTier.free
    return PlanTier.premium


def product_usage(db: Session, user_id: uuid.UUID) -> int:
    """Active (non-deleted) products — soft-deleting frees up quota."""
    return int(
        db.scalar(
            select(func.count(Product.id)).where(
                Product.user_id == user_id, Product.deleted_at.is_(None)
            )
        )
        or 0
    )


def enforce_product_quota(db: Session, user: User) -> None:
    """Raise PlanLimitError when the user cannot add another product."""
    sub = get_or_create(db, user.id)
    limits = limits_for(effective_tier(sub))
    if limits.max_products is None:
        return
    used = product_usage(db, user.id)
    if used >= limits.max_products:
        raise PlanLimitError(
            f"Your free plan covers {limits.max_products} products. "
            "Upgrade to Premium for unlimited products.",
            {"tier": PlanTier.free.value, "limit": limits.max_products, "used": used},
        )


def activate_manual(
    db: Session,
    user: User,
    months: int = 12,
    provider_ref: str | None = None,
) -> Subscription:
    """Grant premium without a store receipt (dev/admin path). Real receipt
    verification replaces this when store billing lands."""
    sub = get_or_create(db, user.id)
    now = utc_now()
    sub.tier = PlanTier.premium
    sub.status = SubscriptionStatus.active
    sub.provider = "manual"
    sub.provider_ref = provider_ref
    sub.started_at = now
    sub.expires_at = add_months(now, months) if months else None
    sub.canceled_at = None
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def cancel(db: Session, user: User) -> Subscription:
    """Cancel premium. A future expires_at is honoured (canceled-but-entitled);
    otherwise access ends immediately."""
    sub = get_or_create(db, user.id)
    now = utc_now()
    sub.canceled_at = now
    expires_at = as_aware(sub.expires_at)
    if expires_at is not None and expires_at > now:
        sub.status = SubscriptionStatus.canceled
    else:
        sub.tier = PlanTier.free
        sub.status = SubscriptionStatus.expired
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub
