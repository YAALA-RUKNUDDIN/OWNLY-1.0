import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.household import Household, HouseholdInvite, HouseholdMember, HouseholdRole
from app.models.product import Product
from app.models.user import User


class HouseholdRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, household_id: uuid.UUID) -> Household | None:
        return self.db.get(Household, household_id)

    def get_member(self, household_id: uuid.UUID, user_id: uuid.UUID) -> HouseholdMember | None:
        return self.db.scalar(
            select(HouseholdMember).where(
                HouseholdMember.household_id == household_id,
                HouseholdMember.user_id == user_id,
            )
        )

    def get_user_household_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        rows = self.db.execute(
            select(HouseholdMember.household_id).where(HouseholdMember.user_id == user_id)
        ).scalars().all()
        return list(rows)

    def list_user_households(self, user_id: uuid.UUID) -> list[dict]:
        memberships = self.db.execute(
            select(HouseholdMember)
            .options(joinedload(HouseholdMember.household))
            .where(HouseholdMember.user_id == user_id)
            .order_by(HouseholdMember.joined_at.desc())
        ).scalars().all()

        results = []
        for m in memberships:
            h = m.household
            # Count members
            member_count = self.db.scalar(
                select(func.count(HouseholdMember.id)).where(HouseholdMember.household_id == h.id)
            ) or 0
            # Count shared active products
            product_count = self.db.scalar(
                select(func.count(Product.id)).where(
                    Product.household_id == h.id,
                    Product.deleted_at.is_(None),
                )
            ) or 0

            results.append({
                "household": h,
                "role": m.role,
                "member_count": member_count,
                "product_count": product_count,
            })
        return results

    def get_household_members(self, household_id: uuid.UUID) -> list[tuple[HouseholdMember, User]]:
        stmt = (
            select(HouseholdMember, User)
            .join(User, HouseholdMember.user_id == User.id)
            .where(HouseholdMember.household_id == household_id)
            .order_by(HouseholdMember.joined_at.asc())
        )
        return list(self.db.execute(stmt).all())

    def create_household(self, name: str, user_id: uuid.UUID) -> Household:
        h = Household(name=name.strip(), created_by_user_id=user_id)
        self.db.add(h)
        self.db.flush()

        admin_member = HouseholdMember(
            household_id=h.id,
            user_id=user_id,
            role=HouseholdRole.admin,
        )
        self.db.add(admin_member)
        self.db.flush()
        return h

    def update_household(self, household_id: uuid.UUID, name: str) -> Household | None:
        h = self.get(household_id)
        if h:
            h.name = name.strip()
            self.db.add(h)
            self.db.flush()
        return h

    def delete_household(self, household_id: uuid.UUID) -> None:
        h = self.get(household_id)
        if h:
            # Unlink products to personal ownership
            products = self.db.execute(
                select(Product).where(Product.household_id == household_id)
            ).scalars().all()
            for p in products:
                p.household_id = None
                self.db.add(p)
            self.db.delete(h)
            self.db.flush()

    def generate_invite_code(self) -> str:
        # Generates human-friendly invite code: OWN-XXXX-XXXX
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        return f"OWN-{part1}-{part2}"

    def create_invite(
        self,
        household_id: uuid.UUID,
        inviter_user_id: uuid.UUID,
        role: HouseholdRole,
        expires_at: datetime,
    ) -> HouseholdInvite:
        code = self.generate_invite_code()
        # Guarantee uniqueness
        while self.db.scalar(select(HouseholdInvite).where(HouseholdInvite.invite_code == code)):
            code = self.generate_invite_code()

        invite = HouseholdInvite(
            household_id=household_id,
            inviter_user_id=inviter_user_id,
            invite_code=code,
            role=role,
            expires_at=expires_at,
        )
        self.db.add(invite)
        self.db.flush()
        return invite

    def list_active_invites(self, household_id: uuid.UUID) -> list[HouseholdInvite]:
        now = datetime.now(timezone.utc)
        return list(
            self.db.execute(
                select(HouseholdInvite).where(
                    HouseholdInvite.household_id == household_id,
                    HouseholdInvite.accepted_at.is_(None),
                    HouseholdInvite.expires_at > now,
                )
            ).scalars().all()
        )

    def get_invite_by_code(self, code: str) -> HouseholdInvite | None:
        return self.db.scalar(
            select(HouseholdInvite).where(
                func.upper(HouseholdInvite.invite_code) == code.strip().upper()
            )
        )

    def add_member(
        self,
        household_id: uuid.UUID,
        user_id: uuid.UUID,
        role: HouseholdRole = HouseholdRole.member,
    ) -> HouseholdMember:
        existing = self.get_member(household_id, user_id)
        if existing:
            return existing

        member = HouseholdMember(
            household_id=household_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        self.db.flush()
        return member

    def remove_member(self, household_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        member = self.get_member(household_id, user_id)
        if member:
            self.db.delete(member)
            self.db.flush()
            return True
        return False
