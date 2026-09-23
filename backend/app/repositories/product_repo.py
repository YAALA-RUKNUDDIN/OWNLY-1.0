"""Product data access. EVERY query is scoped by user_id and user's household
memberships — this is the enforcement point for user isolation and sharing."""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Product, Warranty
from app.models.household import HouseholdMember, HouseholdRole


class ProductRepository:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    def _get_user_household_ids(self) -> list[uuid.UUID]:
        rows = self.db.execute(
            select(HouseholdMember.household_id).where(HouseholdMember.user_id == self.user_id)
        ).scalars().all()
        return list(rows)

    def _base_query(self, scope: str = "all", household_id: uuid.UUID | None = None):
        household_ids = self._get_user_household_ids()

        q = select(Product).options(joinedload(Product.warranties)).where(Product.deleted_at.is_(None))

        if scope == "personal":
            q = q.where(Product.user_id == self.user_id, Product.household_id.is_(None))
        elif scope == "household":
            if household_id:
                if household_id not in household_ids:
                    # User is not a member of this household -> return empty
                    q = q.where(False)
                else:
                    q = q.where(Product.household_id == household_id)
            else:
                if household_ids:
                    q = q.where(Product.household_id.in_(household_ids))
                else:
                    q = q.where(False)
        else:  # "all"
            if household_ids:
                q = q.where(
                    or_(
                        Product.user_id == self.user_id,
                        Product.household_id.in_(household_ids),
                    )
                )
            else:
                q = q.where(Product.user_id == self.user_id)

        return q

    def list(
        self,
        search: str | None = None,
        category: str | None = None,
        status: str | None = None,
        warranty_status: str | None = None,
        purchase_year: int | None = None,
        scope: str = "all",
        household_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Product], int]:
        q = self._base_query(scope=scope, household_id=household_id)

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
            elif warranty_status == "active":
                q = q.where(Product.warranties.any(Warranty.end_date >= now))
            elif warranty_status == "expired":
                q = q.where(Product.warranties.any(Warranty.end_date < now))
            elif warranty_status == "none":
                q = q.where(~Product.warranties.any())

        total = self.db.scalar(select(func.count()).select_from(q.order_by(None).subquery())) or 0
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

    def get_user_role_for_product(self, product: Product) -> str:
        """Returns 'owner', 'admin', 'member', 'viewer', or 'none'."""
        if product.user_id == self.user_id:
            return "owner"
        if product.household_id:
            member = self.db.scalar(
                select(HouseholdMember).where(
                    HouseholdMember.household_id == product.household_id,
                    HouseholdMember.user_id == self.user_id,
                )
            )
            if member:
                return member.role.value
        return "none"

    def can_edit_product(self, product: Product) -> bool:
        role = self.get_user_role_for_product(product)
        return role in ("owner", "admin", "member")

    def create(self, **fields) -> Product:
        product = Product(user_id=self.user_id, **fields)
        self.db.add(product)
        self.db.flush()
        return product

    def soft_delete(self, product: Product) -> None:
        product.deleted_at = datetime.now()
        self.db.add(product)