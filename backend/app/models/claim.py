import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base
from app.models.user import generate_uuid


class ClaimStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    in_review = "in_review"
    approved = "approved"
    repaired = "repaired"
    replaced = "replaced"
    rejected = "rejected"
    closed = "closed"


class WarrantyClaim(Base):
    """Warranty claim tracking record linking products, warranties, and outcomes."""
    __tablename__ = "warranty_claims"
    __table_args__ = (
        Index("ix_warranty_claims_product_id", "product_id"),
        Index("ix_warranty_claims_user_id", "user_id"),
        Index("ix_warranty_claims_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    warranty_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("warranties.id", ondelete="SET NULL"), nullable=True
    )

    claim_reference: Mapped[str | None] = mapped_column(String(100))  # e.g., RMA-123456 or manufacturer case #
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    issue_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claim_status"), default=ClaimStatus.draft, nullable=False
    )
    incident_date: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    claim_cost_covered: Mapped[float | None] = mapped_column(Numeric(12, 2))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product: Mapped["Product"] = relationship(back_populates="claims")
    warranty: Mapped["Warranty | None"] = relationship()
    user: Mapped["User"] = relationship()
