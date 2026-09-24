"""Warranty claim repository with user isolation and household RBAC scoping."""
import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Product, WarrantyClaim
from app.models.household import HouseholdMember


class ClaimRepository:
    def __init__(self, db: Session, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id

    def _get_user_household_ids(self) -> list[uuid.UUID]:
        rows = self.db.execute(
            select(HouseholdMember.household_id).where(HouseholdMember.user_id == self.user_id)
        ).scalars().all()
        return list(rows)

    def _base_query(self):
        household_ids = self._get_user_household_ids()
        q = (
            select(WarrantyClaim)
            .join(WarrantyClaim.product)
            .options(
                joinedload(WarrantyClaim.product),
                joinedload(WarrantyClaim.warranty),
            )
            .where(Product.deleted_at.is_(None))
        )
        if household_ids:
            q = q.where(
                or_(
                    WarrantyClaim.user_id == self.user_id,
                    Product.user_id == self.user_id,
                    Product.household_id.in_(household_ids),
                )
            )
        else:
            q = q.where(
                or_(
                    WarrantyClaim.user_id == self.user_id,
                    Product.user_id == self.user_id,
                )
            )
        return q

    def get(self, claim_id: uuid.UUID) -> Optional[WarrantyClaim]:
        """Fetch claim by ID scoped to caller's personal or household vaults."""
        return (
            self.db.execute(self._base_query().where(WarrantyClaim.id == claim_id))
            .unique()
            .scalars()
            .first()
        )

    def list_for_product(self, product_id: uuid.UUID) -> list[WarrantyClaim]:
        """List all claims filed for a given product."""
        return (
            self.db.execute(
                self._base_query()
                .where(WarrantyClaim.product_id == product_id)
                .order_by(WarrantyClaim.incident_date.desc(), WarrantyClaim.created_at.desc())
            )
            .unique()
            .scalars()
            .all()
        )

    def list_for_user(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[WarrantyClaim], int]:
        """List all claims accessible to the user with optional status filter."""
        q = self._base_query()
        if status:
            q = q.where(WarrantyClaim.status == status)

        count_q = (
            select(func.count(WarrantyClaim.id))
            .join(WarrantyClaim.product)
            .where(Product.deleted_at.is_(None))
        )
        household_ids = self._get_user_household_ids()
        if household_ids:
            count_q = count_q.where(
                or_(
                    WarrantyClaim.user_id == self.user_id,
                    Product.user_id == self.user_id,
                    Product.household_id.in_(household_ids),
                )
            )
        else:
            count_q = count_q.where(
                or_(
                    WarrantyClaim.user_id == self.user_id,
                    Product.user_id == self.user_id,
                )
            )

        if status:
            count_q = count_q.where(WarrantyClaim.status == status)

        total = self.db.scalar(count_q) or 0
        claims = (
            self.db.execute(
                q.order_by(WarrantyClaim.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .unique()
            .scalars()
            .all()
        )
        return list(claims), int(total)

    def create(
        self,
        product_id: uuid.UUID,
        title: str,
        issue_description: str,
        incident_date,
        warranty_id: Optional[uuid.UUID] = None,
        claim_reference: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
    ) -> WarrantyClaim:
        claim = WarrantyClaim(
            user_id=self.user_id,
            product_id=product_id,
            warranty_id=warranty_id,
            title=title,
            issue_description=issue_description,
            incident_date=incident_date,
            claim_reference=claim_reference,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )
        self.db.add(claim)
        self.db.flush()
        return claim

    def update(self, claim: WarrantyClaim, **fields) -> WarrantyClaim:
        for k, v in fields.items():
            if hasattr(claim, k) and v is not None:
                setattr(claim, k, v)
        self.db.add(claim)
        self.db.flush()
        return claim

    def delete(self, claim: WarrantyClaim) -> None:
        self.db.delete(claim)
        self.db.flush()
