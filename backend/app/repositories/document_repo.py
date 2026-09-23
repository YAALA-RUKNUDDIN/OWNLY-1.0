import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document


class DocumentRepository:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    def list_for_product(self, product_id: uuid.UUID) -> list[Document]:
        return (
            self.db.execute(
                select(Document)
                .where(Document.product_id == product_id, Document.user_id == self.user_id)
                .order_by(Document.created_at.desc())
            )
            .scalars()
            .all()
        )

    def get(self, document_id: uuid.UUID) -> Document | None:
        return (
            self.db.execute(
                select(Document).where(Document.id == document_id, Document.user_id == self.user_id)
            )
            .scalar_one_or_none()
        )