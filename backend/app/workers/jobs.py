"""Background jobs: daily warranty/return/reminder scan → notification_log
→ push. Idempotent via the notification_log unique constraint."""
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload

from app.core.analytics_events import AnalyticsEvent
from app.core.database import SessionLocal
from app.core.datetime_utils import utc_now
from app.integrations.analytics import track
from app.integrations.push import get_push
from app.models import (
    DeviceToken, NotificationCategory, NotificationLog, NotificationPreference,
    Product, ProductStatus, Reminder, ReminderStatus, Warranty,
)
from app.services.user_service import parse_lead_days

logger = logging.getLogger("ownly.worker")

MILESTONE_MESSAGES = {
    90: "Your {name} warranty expires in 90 days.",
    30: "Your {name} warranty is expiring next month.",
    7: "Your {name} warranty expires in 7 days.",
    1: "Your {name} warranty expires tomorrow.",
    0: "Your {name} warranty expires today.",
}

REMINDER_CATEGORY_MAP = {
    "warranty_expiry": "warranty",
    "return_expiry": "return_window",
    "service_due": "service",
    "custom": "custom",
}


def _user_prefs(db, user_id) -> dict:
    prefs = (
        db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        ).scalars().all()
    )
    return {
        p.category.value: {"enabled": p.enabled, "lead_days": parse_lead_days(p.lead_days)}
        for p in prefs
    }


def _notify(db, user_id, subject_type, subject_id, milestone, due_date,
            category, title, body, data: dict | None = None) -> bool:
    """Idempotent notify: unique-guard in DB, then push. Returns True if sent."""
    exists = db.scalar(
        select(NotificationLog.id).where(
            NotificationLog.user_id == user_id,
            NotificationLog.subject_type == subject_type,
            NotificationLog.subject_id == subject_id,
            NotificationLog.milestone == milestone,
            NotificationLog.due_date == due_date,
        )
    )
    if exists:
        return False  # duplicate — skip

    log = NotificationLog(
        user_id=user_id, subject_type=subject_type, subject_id=subject_id,
        milestone=milestone, due_date=due_date, category=category,
        title=title, body=body,
    )
    db.add(log)
    db.flush()

    tokens = [
        row[0] for row in db.execute(
            select(DeviceToken.fcm_token).where(DeviceToken.user_id == user_id)
        ).fetchall()
    ]
    payload = {"subject_id": str(subject_id), "subject_type": str(subject_type)}
    if data:
        payload.update(data)
    try:
        invalid = get_push().send(tokens, title, body, payload)
        if invalid:
            db.execute(delete(DeviceToken).where(DeviceToken.fcm_token.in_(invalid)))
    except Exception as e:
        log.delivery_status = "failed"
        logger.error("Push send failed for user %s: %s", user_id, e)
    track(AnalyticsEvent.notification_sent, user_id, {"category": category.value, "milestone": milestone,
                                                      "delivery_status": log.delivery_status})
    return True


def run_daily_scan() -> dict:
    """Runs once per day (scheduler). Safe to re-run: idempotent."""
    db = SessionLocal()
    stats = {"warranty": 0, "return": 0, "reminder": 0}
    try:
        today = datetime.now().date()

        products = (
            db.execute(
                select(Product)
                .options(joinedload(Product.warranties))
                .where(Product.deleted_at.is_(None), Product.status == ProductStatus.active)
            )
            .unique()
            .scalars()
            .all()
        )

        for p in products:
            prefs = _user_prefs(db, p.user_id)

            # --- Warranty milestones (90/30/7/1/0 days) ---
            for w in p.warranties:
                end = w.end_date.date() if isinstance(w.end_date, datetime) else w.end_date
                days = (end - today).days
                wpref = prefs.get("warranty", {"enabled": True, "lead_days": [90, 30, 7, 1, 0]})
                if not wpref["enabled"]:
                    continue
                if days in wpref["lead_days"]:
                    msg = MILESTONE_MESSAGES.get(days, f"Your {p.name} warranty expires in {days} days.")
                    if _notify(db, p.user_id, "warranty", w.id, f"{days}d", end,
                               NotificationCategory.warranty,
                               f"{p.name} warranty", msg.format(name=p.name),
                               data={
                                   "product_id": str(p.id),
                                   "route": f"/products/{p.id}",
                                   "deep_link": f"ownly:///products/{p.id}",
                               }):
                        stats["warranty"] += 1

            # --- Return window ---
            if p.return_days and p.return_days > 0:
                start = p.purchase_date.date() if isinstance(p.purchase_date, datetime) else p.purchase_date
                r_end = start + timedelta(days=p.return_days)
                days = (r_end - today).days
                rpref = prefs.get("return_window", {"enabled": True, "lead_days": [0]})
                if rpref["enabled"] and days in rpref["lead_days"]:
                    msg = (f"Your return window for {p.name} closes today." if days == 0
                           else f"Your return window for {p.name} closes in {days} day(s).")
                    if _notify(db, p.user_id, "return", p.id, f"{days}d", r_end,
                               NotificationCategory.return_window,
                               f"{p.name} return window", msg,
                               data={
                                   "product_id": str(p.id),
                                   "route": f"/products/{p.id}",
                                   "deep_link": f"ownly:///products/{p.id}",
                               }):
                        stats["return"] += 1

        # --- Due reminders (service due, custom, etc.) ---
        due_reminders = (
            db.execute(
                select(Reminder).where(
                    Reminder.status == ReminderStatus.upcoming,
                    Reminder.scheduled_date <= today,
                )
            ).scalars().all()
        )
        for r in due_reminders:
            rtype = r.reminder_type.value if hasattr(r.reminder_type, "value") else r.reminder_type
            cat = REMINDER_CATEGORY_MAP.get(rtype, "custom")
            rpref = prefs_for(db, r.user_id).get(cat, {"enabled": True, "lead_days": [0]})
            if not rpref["enabled"]:
                continue
            rem_route = f"/products/{r.product_id}" if r.product_id else "/reminders"
            rem_deep = f"ownly:///products/{r.product_id}" if r.product_id else "ownly:///reminders"
            if _notify(db, r.user_id, "reminder", r.id, "due", r.scheduled_date,
                       NotificationCategory(cat), r.title, r.description or r.title,
                       data={
                           "product_id": str(r.product_id) if r.product_id else "",
                           "route": rem_route,
                           "deep_link": rem_deep,
                       }):
                stats["reminder"] += 1
                r.notified_at = utc_now()
                db.add(r)

        db.commit()
        logger.info("Daily scan complete: %s", stats)
        return stats
    except Exception:
        db.rollback()
        logger.exception("Daily scan failed")
        raise
    finally:
        db.close()


def prefs_for(db, user_id) -> dict:
    return _user_prefs(db, user_id)