import uuid

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import GUID, Base
from app.models.user import NotificationCategory, generate_uuid


class NotificationLog(Base):
    """Idempotency guard: one notification per (user, subject, milestone, date).

    The daily worker inserts a row before sending; a unique violation means
    the notification was already sent and must be skipped. This makes the
    worker safe to re-run and prevents duplicate pushes.
    """
    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint("user_id", "subject_type", "subject_id", "milestone", "due_date",
                         name="uq_notification_once"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)  # warranty|return|reminder|service
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False)
    milestone: Mapped[str] = mapped_column(String(40), nullable=False)     # e.g. "30d", "7d", "1d", "today"
    due_date: Mapped[object] = mapped_column(Date, nullable=False)
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(NotificationCategory, name="notification_category"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    sent_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delivery_status: Mapped[str] = mapped_column(String(20), default="sent")