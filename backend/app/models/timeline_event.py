import enum
import uuid

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base
from app.models.user import generate_uuid


class EventType(str, enum.Enum):
    product_added = "product_added"
    product_updated = "product_updated"
    product_sold = "product_sold"
    product_archived = "product_archived"
    invoice_uploaded = "invoice_uploaded"
    document_uploaded = "document_uploaded"
    document_deleted = "document_deleted"
    warranty_started = "warranty_started"
    warranty_extended = "warranty_extended"
    warranty_expiring_soon = "warranty_expiring_soon"
    warranty_expired = "warranty_expired"
    service_completed = "service_completed"
    repair_recorded = "repair_recorded"
    reminder_created = "reminder_created"
    reminder_completed = "reminder_completed"
    claim_filed = "claim_filed"
    claim_updated = "claim_updated"
    claim_resolved = "claim_resolved"


class TimelineEvent(Base):
    """Append-only ownership journal. Never updated, only inserted."""
    __tablename__ = "timeline_events"
    __table_args__ = (Index("ix_timeline_product_date", "product_id", "event_date"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_type: Mapped[EventType] = mapped_column(Enum(EventType, name="event_type"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[object] = mapped_column(Date, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="timeline_events")