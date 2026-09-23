import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base
from app.models.user import generate_uuid


class ProductStatus(str, enum.Enum):
    active = "active"
    sold = "sold"
    lost = "lost"
    replaced = "replaced"
    archived = "archived"


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_user_status", "user_id", "status"),
        Index("ix_products_category", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("households.id", ondelete="SET NULL"), index=True, nullable=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120))
    model_number: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="other")
    purchase_date: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    purchase_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    seller: Mapped[str | None] = mapped_column(String(200))
    purchase_location: Mapped[str | None] = mapped_column(String(200))
    serial_number: Mapped[str | None] = mapped_column(String(120))
    imei_number: Mapped[str | None] = mapped_column(String(120))
    sku: Mapped[str | None] = mapped_column(String(120))
    custom_id: Mapped[str | None] = mapped_column(String(120))
    payment_info: Mapped[str | None] = mapped_column(Text)
    return_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 = not tracked
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"), default=ProductStatus.active, nullable=False
    )
    image_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner: Mapped["User"] = relationship(back_populates="products")
    household: Mapped["Household | None"] = relationship(back_populates="products")
    warranties: Mapped[list["Warranty"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    service_records: Mapped[list["ServiceRecord"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    repairs: Mapped[list["Repair"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    timeline_events: Mapped[list["TimelineEvent"]] = relationship(back_populates="product", cascade="all, delete-orphan")