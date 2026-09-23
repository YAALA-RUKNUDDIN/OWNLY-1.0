"""Notification history — what OWNLY has already told this user.

Reads the same `notification_log` rows the daily worker writes (its unique
constraint doubles as the idempotency guard), so history is exact and needs
no extra bookkeeping.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_current_user
from app.core.database import get_db
from app.core.errors import ValidationError
from app.integrations.push import get_push
from app.models import DeviceToken, NotificationCategory, NotificationLog, User
from app.schemas.notification import (
    NotificationListOut,
    TestNotificationRequest,
    TestNotificationResponse,
)

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


@router.post("/test", response_model=TestNotificationResponse)
def send_test_notification(
    req: TestNotificationRequest = TestNotificationRequest(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger an immediate push notification to this user's registered devices.

    Supports custom deep-link and route testing end-to-end.
    """
    tokens = [
        row[0] for row in db.execute(
            select(DeviceToken.fcm_token).where(DeviceToken.user_id == user.id)
        ).fetchall()
    ]

    route = req.route
    if not route.startswith("/"):
        route = f"/{route}"
    deep_link = req.deep_link or f"ownly:///{route.lstrip('/')}"
    subject_id = uuid.uuid4()

    data = {
        "route": route,
        "deep_link": deep_link,
        "subject_type": "test",
        "subject_id": str(subject_id),
    }

    delivery_status = "sent" if tokens else "no_devices"
    if tokens:
        try:
            invalid = get_push().send(tokens, req.title, req.body, data)
            if invalid:
                db.execute(delete(DeviceToken).where(DeviceToken.fcm_token.in_(invalid)))
        except Exception:
            delivery_status = "failed"

    log = NotificationLog(
        user_id=user.id,
        subject_type="test",
        subject_id=subject_id,
        milestone=f"test-{datetime.now(timezone.utc).strftime('%H%M%S%f')}",
        due_date=datetime.now(timezone.utc).date(),
        category=NotificationCategory.custom,
        title=req.title,
        body=req.body,
        delivery_status=delivery_status,
    )
    db.add(log)
    db.commit()

    return {
        "message": "Test notification dispatched." if tokens else "Test notification logged (no registered devices).",
        "recipient_count": len(tokens),
        "tokens": tokens,
        "route": route,
        "deep_link": deep_link,
    }
