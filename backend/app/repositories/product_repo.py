"""Product data access. EVERY query is scoped by user_id — this is the
enforcement point for user isolation."""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Product, Warranty


class ProductRepository:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    def _base_query(self):
        return (
            select(Product)
            .options(joinedload(Product.warranties))
            .where(Product.user_id == self.user_id, Product.deleted_at.is_(None))
        )

    def list(
        self,
        search: str | None = None,
        category: str | None = None,
        status: str | None = None,
        warranty_status: str | None = None,
        purchase_year: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:
        q = self._base_query()

        if search:
            pattern = f"%{search.strip().lower()}%"
            q = q.where(
                or_(
                    func.lower(Product.name).like(pattern),
                    func.lower(func.coalesce(Product.brand, "")).like(pattern),
                    func.lower(func.coalesce(Product.model_number, "")).like(pattern),
                    func.lower(func.coalesce(Product.serial_number, "")).like(pattern),
                )
            )
        if category:
            q = q.where(Product.category == category)
        if status:
            q = q.where(Product.status == status)
        if purchase_year:
            q = q.where(func.extract("year", Product.purchase_date) == purchase_year)

        if warranty_status:
            now = datetime.now()
            in_30 = datetime.combine(now.date() + timedelta(days=30), datetime.min.time())
            if warranty_status == "expiring":
                # Warranty still valid but ending within 30 days
                q = q.where(
                    Product.warranties.any(
                        (Warranty.end_date >= now) & (Warranty.end_date < in_30)
                    )
                )
            elif warranty_status == "valid":
                q = q.where(Product.warranties.any(Warranty.end_date >= now))
            elif warranty_status == "expired":
                q = q.where(
                    Product.warranties.any() & ~Product.warranties.any(Warranty.end_date >= now)
                )
            elif warranty_status == "none":
                q = q.where(~Product.warranties.any())

        total = self.db.scalar(select(func.count()).select_from(q.subquery())) or 0
        rows = (
            self.db.execute(
                q.order_by(Product.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .unique()
            .scalars()
            .all()
        )
        return rows, int(total)

    def get(self, product_id: uuid.UUID) -> Product | None:
        return (
            self.db.execute(self._base_query().where(Product.id == product_id))
            .unique()
            .scalars()
            .first()
        )

    def get_with_documents(self, product_id: uuid.UUID) -> Product | None:
        return (
            self.db.execute(
                self._base_query()
                .options(joinedload(Product.documents), joinedload(Product.repairs), joinedload(Product.service_records))
                .where(Product.id == product_id)
            )
            .unique()
            .scalars()
            .first()
        )

    def create(self, **fields) -> Product:
        product = Product(user_id=self.user_id, **fields)
        self.db.add(product)
        self.db.flush()
        return product

    def soft_delete(self, product: Product) -> None:
        from datetime import datetime as dt
        product.deleted_at = datetime.now()
        self.db.add(product)