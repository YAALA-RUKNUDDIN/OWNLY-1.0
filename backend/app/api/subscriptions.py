"""Subscription endpoints: read entitlement, dev activation, cancellation."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.analytics_events import AnalyticsEvent
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ForbiddenError
from app.integrations.analytics import track
from app.models import PlanTier, User
from app.schemas.subscription import ActivateRequest, SubscriptionLimits, SubscriptionOut, SubscriptionUsage
from app.services import subscription_service

router = APIRouter(prefix="/subscription", tags=["subscription"])


def _serialize(db: Session, user: User) -> dict:
    sub = subscription_service.get_or_create(db, user.id)
    tier = subscription_service.effective_tier(sub)
    limits = subscription_service.limits_for(tier)
    return {
        "tier": tier,
        "status": sub.status.value if hasattr(sub.status, "value") else str(sub.status),
        "provider": sub.provider,
        "started_at": sub.started_at,
        "expires_at": sub.expires_at,
        "canceled_at": sub.canceled_at,
        "limits": SubscriptionLimits(max_products=limits.max_products, features=list(limits.features)),
        "usage": SubscriptionUsage(products=subscription_service.product_usage(db, user.id)),
    }


@router.get("", response_model=SubscriptionOut)
def get_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Current plan, limits and usage — the mobile app drives feature gating
    and upgrade prompts from this single call."""
    result = _serialize(db, user)
    db.commit()  # persist the lazily-created free subscription
    return result


@router.post("/activate", response_model=SubscriptionOut)
def activate_subscription(
    body: ActivateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grant premium. Development/admin convenience stub — store receipt
    verification replaces this once real billing lands (D-007)."""
    if settings.is_production:
        raise ForbiddenError("Subscription activation requires a verified store receipt in production.")
    subscription_service.activate_manual(db, user, months=body.months, provider_ref=body.provider_ref)
    track(AnalyticsEvent.subscription_activated, user.id, {"tier": PlanTier.premium.value, "months": body.months})
    return _serialize(db, user)


@router.post("/cancel", response_model=SubscriptionOut)
def cancel_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel premium. Keeps entitlement until expires_at when one is set."""
    subscription_service.cancel(db, user)
    track(AnalyticsEvent.subscription_canceled, user.id)
    return _serialize(db, user)
