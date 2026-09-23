"""TodayService — the heart of OWNLY.

Answers: "What do I need to do about the things I own today?"

Design:
  1. Pure classification functions (no DB) — independently unit-testable.
  2. build_today_dashboard(db, user_id) — thin DB layer that feeds the
     classifiers and assembles the response sorted by urgency.

Buckets:
  attention  — action required now (or very soon). Sorted: severity →
               days remaining.
  upcoming   — dated events beyond the attention window, within the
               horizon. Sorted: days remaining.
  everything else — not surfaced; stats carry the counts.

Only ACTIVE, non-deleted products are evaluated. Sold/archived products
have left the ownership lifecycle and generate no noise.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Document,
    Product,
    ProductStatus,
    Reminder,
    ReminderStatus,
    ServiceRecord,
    User,
)
from app.schemas.dashboard import (
    AttentionItem,
    DashboardStats,
    RecentlyAddedItem,
    TodayDashboard,
    UpcomingItem,
)

# Attention thresholds — tuned so the Today screen mirrors the product
# spec: "Warranty expires in 14 days" must land in NEEDS ATTENTION.
WARRANTY_ATTENTION_DAYS = 30       # mirrors warranty_service.EXPIRING_SOON_DAYS
WARRANTY_EXPIRED_GRACE_DAYS = 30   # recently-expired warranties stay visible briefly
RETURN_ATTENTION_DAYS = 5          # mirrors warranty_service.RETURN_EXPIRING_SOON_DAYS
RETURN_CRITICAL_DAYS = 2           # "2 days remaining", "last day" per spec
REMINDER_ATTENTION_DAYS = 7        # due within a week = act now
UPCOMING_HORIZON_DAYS = 120        # how far ahead "Upcoming" looks

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _as_date(value: datetime | date) -> date:
    return value.date() if isinstance(value, datetime) else value


def classify_warranty(end_date: datetime | date, today: date):
    """Returns (bucket, kind, severity, days_remaining, due_date) | None.

    bucket: "attention" | "upcoming".
    """
    end = _as_date(end_date)
    days = (end - today).days
    if days < -WARRANTY_EXPIRED_GRACE_DAYS:
        return None  # long expired — history, not action
    if days < 0:
        return "attention", "warranty_expired", "info", days, end
    if days <= WARRANTY_ATTENTION_DAYS:
        severity = "critical" if days <= 7 else "warning"
        return "attention", "warranty_expiring", severity, days, end
    if days <= UPCOMING_HORIZON_DAYS:
        return "upcoming", "warranty_expiring", "info", days, end
    return None


def classify_return(purchase_date: datetime | date, return_days: int | None, today: date):
    if not return_days or return_days <= 0:
        return None
    start = _as_date(purchase_date)
    end = start + timedelta(days=return_days)
    days = (end - today).days
    if days < 0:
        return None  # window closed — nothing actionable
    if days <= RETURN_ATTENTION_DAYS:
        severity = "critical" if days <= RETURN_CRITICAL_DAYS else "warning"
        return "attention", "return_expiring", severity, days, end
    if days <= UPCOMING_HORIZON_DAYS:
        return "upcoming", "return_expiring", "info", days, end
    return None


def classify_service(next_service_date: datetime | date, today: date):
    nxt = _as_date(next_service_date)
    days = (nxt - today).days
    if days > UPCOMING_HORIZON_DAYS:
        return None
    if days <= 7:  # overdue or imminent
        return "attention", "service_due", "critical", days, nxt
    if days <= WARRANTY_ATTENTION_DAYS:
        return "attention", "service_due", "warning", days, nxt
    return "upcoming", "service_due", "info", days, nxt


def classify_reminder(scheduled_date: date, today: date):
    days = (scheduled_date - today).days
    if days > UPCOMING_HORIZON_DAYS:
        return None
    if days <= REMINDER_ATTENTION_DAYS:
        severity = "critical" if days <= 0 else "warning"
        return "attention", "reminder_due", severity, days, scheduled_date
    return "upcoming", "reminder_due", "info", days, scheduled_date


def build_greeting(now_hour: int, user_name: str | None) -> str:
    base = "Good morning" if now_hour < 12 else "Good afternoon" if now_hour < 18 else "Good evening"
    first = (user_name or "").strip().split(" ")[0] if user_name else ""
    return f"{base}, {first}" if first else base

def build_today_dashboard(db: Session, user_id) -> TodayDashboard:
    today = datetime.now().date()

    products = (
        db.execute(
            select(Product)
            .options(selectinload(Product.warranties))
            .where(
                Product.user_id == user_id,
                Product.deleted_at.is_(None),
                Product.status == ProductStatus.active,
            )
        )
        .scalars()
        .all()
    )

    attention: list[AttentionItem] = []
    upcoming: list[UpcomingItem] = []

    def _add(result, product: Product | None):
        if result is None:
            return
        bucket, kind, severity, days, due = result
        if bucket == "attention":
            attention.append(AttentionItem(
                kind=kind, severity=severity,
                product_id=product.id if product else None,
                product_name=product.name if product else None,
                title=kind.replace("_", " ").capitalize(),
                message=_message(kind, product, days, due),
                due_date=due, days_remaining=days,
            ))
        else:
            upcoming.append(UpcomingItem(
                kind=kind,
                product_id=product.id if product else None,
                product_name=product.name if product else None,
                title=kind.replace("_", " ").capitalize(),
                due_date=due, days_remaining=days,
            ))

    for p in products:
        for w in p.warranties:
            _add(classify_warranty(w.end_date, today), p)
        _add(classify_return(p.purchase_date, p.return_days, today), p)

    reminders = (
        db.execute(
            select(Reminder).where(
                Reminder.user_id == user_id,
                Reminder.status == ReminderStatus.upcoming,
                Reminder.scheduled_date <= today + timedelta(days=UPCOMING_HORIZON_DAYS),
            )
        )
        .scalars()
        .all()
    )
    for r in reminders:
        _add(classify_reminder(r.scheduled_date, today), r.product)

    next_services = (
        db.execute(
            select(ServiceRecord)
            .join(Product, ServiceRecord.product_id == Product.id)
            .where(
                Product.user_id == user_id,
                Product.deleted_at.is_(None),
                Product.status == ProductStatus.active,
                ServiceRecord.next_service_date.is_not(None),
                ServiceRecord.next_service_date <= today + timedelta(days=UPCOMING_HORIZON_DAYS),
            )
        )
        .scalars()
        .all()
    )
    for s in next_services:
        _add(classify_service(s.next_service_date, today), s.product)

    # Urgency sort: severity → closest date → stable order.
    attention.sort(key=lambda a: (_SEVERITY_ORDER.get(a.severity, 9), a.days_remaining))
    upcoming.sort(key=lambda u: u.days_remaining)

    # De-duplicate identical (product, kind, date) rows — e.g. two
    # warranties expiring the same day produce one actionable item.
    seen: set = set()
    unique_attention: list[AttentionItem] = []
    for a in attention:
        key = (a.product_id, a.kind, a.due_date)
        if key not in seen:
            seen.add(key)
            unique_attention.append(a)
    attention = unique_attention

    recently_added = [
        RecentlyAddedItem(
            product_id=p.id, name=p.name, brand=p.brand, category=p.category,
            image_url=p.image_url, created_at=p.created_at,
        )
        for p in sorted(products, key=lambda x: x.created_at or datetime.min, reverse=True)[:5]
    ]

    active_warranties = 0
    expiring_warranties = 0
    for p in products:
        for w in p.warranties:
            days = (_as_date(w.end_date) - today).days
            if days >= 0:
                active_warranties += 1
                if days <= WARRANTY_ATTENTION_DAYS:
                    expiring_warranties += 1

    documents_stored = db.scalar(
        select(func.count()).select_from(Document).where(Document.user_id == user_id)
    ) or 0

    user = db.get(User, user_id)

    return TodayDashboard(
        greeting=build_greeting(datetime.now().hour, user.name if user else None),
        attention=attention,
        upcoming=upcoming,
        recently_added=recently_added,
        stats=DashboardStats(
            total_products=len(products),
            active_warranties=active_warranties,
            expiring_warranties=expiring_warranties,
            documents_stored=documents_stored,
        ),
    )


def _message(kind: str, product: Product | None, days: int, due) -> str:
    name = product.name if product else "This product"
    if kind == "warranty_expiring":
        if days == 0:
            return f"The warranty for {name} expires today."
        return f"The warranty for {name} expires in {days} day(s)."
    if kind == "warranty_expired":
        return f"The warranty for {name} has expired. Consider extended coverage or remove it."
    if kind == "return_expiring":
        if days == 0:
            return f"Today is the last day to return {name}."
        return f"The return window for {name} closes in {days} day(s)."
    if kind == "service_due":
        if days < 0:
            return f"{name} is overdue for service ({abs(days)} day(s) past due)."
        if days == 0:
            return f"{name} is due for service today."
        return f"{name} service is due in {days} day(s)."
    if kind == "reminder_due":
        if days < 0:
            return f"Reminder for {name} is overdue."
        if days == 0:
            return f"Reminder for {name} is due today."
        return f"Reminder for {name} is due in {days} day(s)."
    return str(due)
