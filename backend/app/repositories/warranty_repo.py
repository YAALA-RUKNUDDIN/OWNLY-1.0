import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Warranty


class WarrantyRepository:
    def __init__(self, db: Session, user_id: uuid.UUID | None = None):
        self.db = db
        self.user_id = user_id

    def get_for_user(self, warranty_id: uuid.UUID) -> Warranty | None:
        """Fetch a warranty, verifying ownership through its product."""
        return (
            self.db.execute(
                select(Warranty)
                .join(Warranty.product)
                .where(Warranty.id == warranty_id, Warranty.product.property.mapper.class_.user_id == self.user_id)
            )
            .scalar_one_or_none()
        )