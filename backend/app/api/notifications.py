"""Notification history — what OWNLY has already told this user.

Reads the same `notification_log` rows the daily worker writes (its unique
constraint doubles as the idempotency guard), so history is exact and needs
no extra bookkeeping.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_current_user
from app.core.database import get_db
from app.core.errors import ValidationError
from app.models import NotificationCategory, NotificationLog, User
from app.schemas.notification import NotificationListOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListOut)
def list_notifications(
    category: str | None = Query(None, description="warranty | return_window | service | custom"),
    subject_type: str | None = Query(None, description="warranty | return | reminder | service"),
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Most recent notifications first, scoped to the current user."""
    if category and category not in NotificationCategory.__members__:
        raise ValidationError("Unknown notification category.",
                              {"fields": {"category": "unknown category"}})

    query = select(NotificationLog).where(NotificationLog.user_id == user.id)
    if category:
        query = query.where(NotificationLog.category == NotificationCategory[category])
    if subject_type:
        query = query.where(NotificationLog.subject_type == subject_type.strip().lower())

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = (
        db.execute(
            query.order_by(NotificationLog.sent_at.desc(), NotificationLog.id.desc())
            .offset((pagination.page - 1) * pagination.page_size)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )
    return {
        "items": rows,
        "total": int(total),
        "page": pagination.page,
        "page_size": pagination.page_size,
    }
