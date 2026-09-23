import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base
from app.models.user import generate_uuid


class WarrantyType(str, enum.Enum):
    manufacturer = "manufacturer"
    extended = "extended"
    store = "store"
    third_party = "third_party"


class Warranty(Base):
    __tablename__ = "warranties"
    __table_args__ = (Index("ix_warranties_end_date", "end_date"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str | None] = mapped_column(String(200))
    warranty_type: Mapped[WarrantyType] = mapped_column(
        Enum(WarrantyType, name="warranty_type"), default=WarrantyType.manufacturer, nullable=False
    )
    start_date: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_months: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product: Mapped["Product"] = relationship(back_populates="warranties")