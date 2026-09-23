import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Document, Product
from app.models.household import HouseholdMember


class DocumentRepository:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    def _accessible_clause(self):
        household_ids = list(
            self.db.execute(
                select(HouseholdMember.household_id).where(HouseholdMember.user_id == self.user_id)
            ).scalars().all()
        )
        if household_ids:
            return or_(
                Document.user_id == self.user_id,
                Product.household_id.in_(household_ids),
            )
        return Document.user_id == self.user_id

    def list_for_product(self, product_id: uuid.UUID) -> list[Document]:
        return (
            self.db.execute(
                select(Document)
                .join(Product, Document.product_id == Product.id)
                .where(
                    Document.product_id == product_id,
                    Product.deleted_at.is_(None),
                    self._accessible_clause(),
                )
                .order_by(Document.created_at.desc())
            )
            .scalars()
            .all()
        )

    def get(self, document_id: uuid.UUID) -> Document | None:
        return (
            self.db.execute(
                select(Document)
                .join(Product, Document.product_id == Product.id)
                .where(
                    Document.id == document_id,
                    Product.deleted_at.is_(None),
                    self._accessible_clause(),
                )
            )
            .scalar_one_or_none()
        )