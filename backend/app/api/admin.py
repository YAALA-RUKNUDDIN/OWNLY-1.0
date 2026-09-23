"""Admin endpoints — restricted to is_admin users. Aggregate stats only;
never exposes private user documents."""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import ForbiddenError
from app.models import Document, NotificationLog, PlanTier, Product, Subscription, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
def admin_stats(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.is_admin:
        raise ForbiddenError("Admin access required.")
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_products = db.scalar(select(func.count(Product.id))) or 0
    total_documents = db.scalar(select(func.count(Document.id))) or 0
    total_notifications = db.scalar(select(func.count(NotificationLog.id))) or 0
    failed_notifications = db.scalar(
        select(func.count(NotificationLog.id)).where(NotificationLog.delivery_status != "sent")
    ) or 0
    premium_subscriptions = db.scalar(
        select(func.count(Subscription.id)).where(Subscription.tier == PlanTier.premium)
    ) or 0
    return {
        "total_users": int(total_users),
        "total_products": int(total_products),
        "total_documents": int(total_documents),
        "total_notifications_sent": int(total_notifications),
        "failed_notifications": int(failed_notifications),
        "premium_subscriptions": int(premium_subscriptions),
    }