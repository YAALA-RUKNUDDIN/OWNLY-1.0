import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.household import Household, HouseholdInvite, HouseholdMember, HouseholdRole
from app.models.product import Product
from app.repositories.household_repo import HouseholdRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.household import HouseholdDetailOut, HouseholdMemberOut, HouseholdOut


class HouseholdService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = HouseholdRepository(db)

    def create_household(self, user_id: uuid.UUID, name: str) -> HouseholdOut:
        h = self.repo.create_household(name, user_id)
        self.db.commit()
        return HouseholdOut(
            id=h.id,
            name=h.name,
            created_by_user_id=h.created_by_user_id,
            current_user_role="admin",
            member_count=1,
            product_count=0,
            created_at=h.created_at,
        )

    def list_user_households(self, user_id: uuid.UUID) -> list[HouseholdOut]:
        items = self.repo.list_user_households(user_id)
        return [
            HouseholdOut(
                id=item["household"].id,
                name=item["household"].name,
                created_by_user_id=item["household"].created_by_user_id,
                current_user_role=item["role"].value,
                member_count=item["member_count"],
                product_count=item["product_count"],
                created_at=item["household"].created_at,
            )
            for item in items
        ]

    def get_household_detail(self, household_id: uuid.UUID, user_id: uuid.UUID) -> HouseholdDetailOut:
        h = self.repo.get(household_id)
        if not h:
            raise NotFoundError("Household not found.")

        current_member = self.repo.get_member(household_id, user_id)
        if not current_member:
            raise NotFoundError("Household not found.")

        member_rows = self.repo.get_household_members(household_id)
        members_out = [
            HouseholdMemberOut(
                user_id=user.id,
                name=user.name,
                email=user.email,
                role=member.role.value,
                joined_at=member.joined_at,
            )
            for member, user in member_rows
        ]

        product_count = ProductRepository(self.db, user_id)._base_query(
            scope="household", household_id=household_id
        )
        p_count = len(self.db.execute(product_count).unique().scalars().all())

        return HouseholdDetailOut(
            id=h.id,
            name=h.name,
            created_by_user_id=h.created_by_user_id,
            current_user_role=current_member.role.value,
            member_count=len(members_out),
            product_count=p_count,
            created_at=h.created_at,
            members=members_out,
        )

    def update_household(self, household_id: uuid.UUID, user_id: uuid.UUID, name: str) -> HouseholdOut:
        member = self.repo.get_member(household_id, user_id)
        if not member:
            raise NotFoundError("Household not found.")
        if member.role != HouseholdRole.admin:
            raise ForbiddenError("Only household admins can rename the household.")

        h = self.repo.update_household(household_id, name)
        self.db.commit()
        detail = self.get_household_detail(household_id, user_id)
        return detail

    def delete_household(self, household_id: uuid.UUID, user_id: uuid.UUID) -> None:
        h = self.repo.get(household_id)
        if not h:
            raise NotFoundError("Household not found.")
        member = self.repo.get_member(household_id, user_id)
        if not member or member.role != HouseholdRole.admin:
            raise ForbiddenError("Only household admins can delete the household.")

        self.repo.delete_household(household_id)
        self.db.commit()

    def create_invite(
        self,
        household_id: uuid.UUID,
        user_id: uuid.UUID,
        role: HouseholdRole,
        expires_in_days: int = 7,
    ) -> HouseholdInvite:
        member = self.repo.get_member(household_id, user_id)
        if not member:
            raise NotFoundError("Household not found.")
        if member.role != HouseholdRole.admin:
            raise ForbiddenError("Only household admins can generate invite codes.")

        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        invite = self.repo.create_invite(household_id, user_id, role, expires_at)
        self.db.commit()
        return invite

    def list_active_invites(self, household_id: uuid.UUID, user_id: uuid.UUID) -> list[HouseholdInvite]:
        member = self.repo.get_member(household_id, user_id)
        if not member:
            raise NotFoundError("Household not found.")
        if member.role != HouseholdRole.admin:
            raise ForbiddenError("Only household admins can list invites.")

        return self.repo.list_active_invites(household_id)

    def join_household(self, user_id: uuid.UUID, invite_code: str) -> HouseholdOut:
        invite = self.repo.get_invite_by_code(invite_code)
        if not invite:
            raise NotFoundError("Invalid or expired invite code.")

        now = datetime.now(timezone.utc)
        # Check expiry
        exp = invite.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= now:
            raise ValidationError("This invite code has expired.")

        # Check if user already member
        existing = self.repo.get_member(invite.household_id, user_id)
        if existing:
            return self.get_household_detail(invite.household_id, user_id)

        # Add member with role
        self.repo.add_member(invite.household_id, user_id, invite.role)
        invite.accepted_at = now
        self.db.commit()
        return self.get_household_detail(invite.household_id, user_id)

    def remove_member(
        self,
        household_id: uuid.UUID,
        caller_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        caller_member = self.repo.get_member(household_id, caller_user_id)
        if not caller_member:
            raise NotFoundError("Household not found.")

        target_member = self.repo.get_member(household_id, target_user_id)
        if not target_member:
            raise NotFoundError("Member not found in household.")

        # If caller is leaving themselves
        if caller_user_id == target_user_id:
            # Prevent lone admin from leaving without transferring or deleting
            all_members = self.repo.get_household_members(household_id)
            admins = [m for m, u in all_members if m.role == HouseholdRole.admin]
            if len(admins) == 1 and admins[0].user_id == caller_user_id and len(all_members) > 1:
                raise ForbiddenError("You are the only admin. Promote another member before leaving or delete the household.")
        else:
            # Caller must be admin to remove someone else
            if caller_member.role != HouseholdRole.admin:
                raise ForbiddenError("Only household admins can remove other members.")

        self.repo.remove_member(household_id, target_user_id)
        self.db.commit()

    def share_product(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        household_id: uuid.UUID | None,
    ) -> Product:
        product_repo = ProductRepository(self.db, user_id)
        product = product_repo.get(product_id)
        if not product:
            raise NotFoundError("Product not found.")

        # Only the owner or an admin of the product's current household can change sharing
        role = product_repo.get_user_role_for_product(product)
        if role not in ("owner", "admin"):
            raise ForbiddenError("Only the product owner or a household admin can change product sharing.")

        # If sharing to a household, verify user is a member/admin of the target household
        if household_id is not None:
            target_membership = self.repo.get_member(household_id, user_id)
            if not target_membership:
                raise NotFoundError("Destination household not found.")
            if target_membership.role == HouseholdRole.viewer:
                raise ForbiddenError("Viewers cannot share products to the household.")

        product.household_id = household_id
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product
