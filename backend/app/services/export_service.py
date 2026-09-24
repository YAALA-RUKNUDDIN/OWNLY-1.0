"""Full user data export (privacy-first: users own their data)."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.datetime_utils import utc_now
from app.models import (
    Document, NotificationLog, Product, Reminder, Repair, ServiceRecord,
    Subscription, TimelineEvent, User, Warranty,
)


def build_export(db: Session, user_id: uuid.UUID) -> dict:
    products = (
        db.execute(
            select(Product)
            .options(
                joinedload(Product.warranties),
                joinedload(Product.documents),
                joinedload(Product.reminders),
                joinedload(Product.service_records),
                joinedload(Product.repairs),
                joinedload(Product.timeline_events),
                joinedload(Product.claims),
            )
            .where(Product.user_id == user_id)
        )
        .unique()
        .scalars()
        .all()
    )

    subscription = db.scalar(select(Subscription).where(Subscription.user_id == user_id))
    notifications = (
        db.execute(
            select(NotificationLog)
            .where(NotificationLog.user_id == user_id)
            .order_by(NotificationLog.sent_at.desc())
        )
        .scalars()
        .all()
    )

    def iso(d):
        return d.isoformat() if d else None

    return {
        "exported_at": utc_now().isoformat(),
        "profile": {"id": str(user_id)},
        "subscription": None if subscription is None else {
            "tier": subscription.tier.value,
            "status": subscription.status.value,
            "provider": subscription.provider,
            "started_at": iso(subscription.started_at),
            "expires_at": iso(subscription.expires_at),
        },
        "notifications": [
            {"category": n.category.value, "title": n.title, "body": n.body,
             "milestone": n.milestone, "due_date": iso(n.due_date), "sent_at": iso(n.sent_at)}
            for n in notifications
        ],
        "products": [
            {
                "name": p.name,
                "brand": p.brand,
                "model_number": p.model_number,
                "category": p.category,
                "purchase_date": iso(p.purchase_date),
                "purchase_price": float(p.purchase_price) if p.purchase_price else None,
                "currency": p.currency,
                "seller": p.seller,
                "serial_number": p.serial_number,
                "status": p.status.value if p.status else None,
                "warranties": [
                    {"provider": w.provider, "type": w.warranty_type.value,
                     "start": iso(w.start_date), "end": iso(w.end_date)}
                    for w in p.warranties
                ],
                "documents": [
                    {"name": d.document_name, "type": d.document_type.value, "uploaded": iso(d.created_at)}
                    for d in p.documents
                ],
                "reminders": [
                    {"title": r.title, "date": iso(r.scheduled_date), "status": r.status.value}
                    for r in p.reminders
                ],
                "service_records": [
                    {"date": iso(s.service_date), "provider": s.provider,
                     "cost": float(s.cost) if s.cost else None}
                    for s in p.service_records
                ],
                "repairs": [
                    {"date": iso(r.repair_date), "description": r.description,
                     "provider": r.provider, "cost": float(r.cost) if r.cost else None}
                    for r in p.repairs
                ],
                "timeline": [
                    {"type": e.event_type.value, "title": e.title, "date": iso(e.event_date)}
                    for e in p.timeline_events
                ],
                "claims": [
                    {"title": c.title, "status": c.status.value, "claim_reference": c.claim_reference,
                     "incident_date": iso(c.incident_date), "issue": c.issue_description,
                     "cost_covered": float(c.claim_cost_covered) if c.claim_cost_covered else None}
                    for c in p.claims
                ],
            }
            for p in products
        ],
    }