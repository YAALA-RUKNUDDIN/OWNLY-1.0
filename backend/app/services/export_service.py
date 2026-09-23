"""Full user data export (privacy-first: users own their data)."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Document, Product, Reminder, Repair, ServiceRecord, TimelineEvent, User, Warranty,
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
            )
            .where(Product.user_id == user_id)
        )
        .unique()
        .scalars()
        .all()
    )

    def iso(d):
        return d.isoformat() if d else None

    return {
        "exported_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "profile": {"id": str(user_id)},
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
            }
            for p in products
        ],
    }