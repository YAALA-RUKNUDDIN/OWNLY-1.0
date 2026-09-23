"""Subscription / plan tier model.

OWNLY monetization: a free tier capped at a fixed number of active products
and a premium tier with unlimited products plus extra features. One row per
user (created lazily on first read so existing accounts work unchanged).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base
from app.models.user import generate_uuid, utcnow


class PlanTier(str, enum.Enum):
    free = "free"
    premium = "premium"


class SubscriptionStatus(str, enum.Enum):
    active = "active"      # currently entitled to the tier
    canceled = "canceled"  # user cancelled — entitlement runs until expires_at
    expired = "expired"    # entitlement ended (or was revoked)


class Subscription(Base):
    """User entitlement state.

    `provider` records how the tier was granted: `none` (free default),
    `manual` (dev/admin grant), or a future store/PSP identifier
    (`apple`, `google`, `stripe`) once real receipt verification lands.

    Entitlement is COMPUTED at read time from `tier`/`status`/`expires_at`
    (`subscription_service.effective_tier`) so an elapsed premium period
    downgrades automatically — never a stale flag.
    """
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    tier: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier, name="plan_tier"), default=PlanTier.free, nullable=False
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"), default=SubscriptionStatus.active, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(40), default="none", nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="subscription")
