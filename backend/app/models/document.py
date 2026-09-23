import enum
import uuid

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base
from app.models.user import generate_uuid


class DocumentType(str, enum.Enum):
    invoice = "invoice"
    receipt = "receipt"
    warranty_card = "warranty_card"
    insurance = "insurance"
    service_document = "service_document"
    repair_receipt = "repair_receipt"
    manual = "manual"
    other = "other"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_product_user", "product_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type"), default=DocumentType.other, nullable=False
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)  # storage key, never public
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="documents")