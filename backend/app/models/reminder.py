import enum
import uuid

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base
from app.models.user import generate_uuid


class ReminderType(str, enum.Enum):
    warranty_expiry = "warranty_expiry"
    return_expiry = "return_expiry"
    service_due = "service_due"
    custom = "custom"


class ReminderStatus(str, enum.Enum):
    upcoming = "upcoming"
    completed = "completed"
    dismissed = "dismissed"


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (Index("ix_reminders_user_date_status", "user_id", "scheduled_date", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    reminder_type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType, name="reminder_type"), default=ReminderType.custom, nullable=False
    )
    scheduled_date: Mapped[object] = mapped_column(Date, nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus, name="reminder_status"), default=ReminderStatus.upcoming, nullable=False
    )
    recurrence_months: Mapped[int | None] = mapped_column(nullable=True)  # None = one-off
    notified_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product: Mapped["Product | None"] = relationship(back_populates="reminders")