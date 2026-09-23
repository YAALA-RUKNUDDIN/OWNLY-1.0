import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import GUID, Base
from app.models.user import generate_uuid


def utcnow():
    return datetime.now(timezone.utc)


class HouseholdRole(str, enum.Enum):
    admin = "admin"
    member = "member"
    viewer = "viewer"


class Household(Base):
    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow
    )

    creator: Mapped["User"] = relationship(foreign_keys=[created_by_user_id])
    members: Mapped[list["HouseholdMember"]] = relationship(
        back_populates="household", cascade="all, delete-orphan"
    )
    invites: Mapped[list["HouseholdInvite"]] = relationship(
        back_populates="household", cascade="all, delete-orphan"
    )
    products: Mapped[list["Product"]] = relationship(back_populates="household")


class HouseholdMember(Base):
    __tablename__ = "household_members"
    __table_args__ = (
        UniqueConstraint("household_id", "user_id", name="uq_household_member"),
        Index("ix_household_members_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    household_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("households.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[HouseholdRole] = mapped_column(
        Enum(HouseholdRole, name="household_role"), default=HouseholdRole.member, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    household: Mapped["Household"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()


class HouseholdInvite(Base):
    __tablename__ = "household_invites"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=generate_uuid)
    household_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("households.id", ondelete="CASCADE"), index=True, nullable=False
    )
    inviter_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    role: Mapped[HouseholdRole] = mapped_column(
        Enum(HouseholdRole, name="household_role"), default=HouseholdRole.member, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    household: Mapped["Household"] = relationship(back_populates="invites")
    inviter: Mapped["User"] = relationship(foreign_keys=[inviter_user_id])
