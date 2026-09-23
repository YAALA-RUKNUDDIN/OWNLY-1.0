import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HouseholdRoleLiteral = Literal["admin", "member", "viewer"]


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class HouseholdUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class HouseholdMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    name: str
    email: str
    role: HouseholdRoleLiteral
    joined_at: datetime


class HouseholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_by_user_id: uuid.UUID
    current_user_role: HouseholdRoleLiteral
    member_count: int
    product_count: int = 0
    created_at: datetime


class HouseholdDetailOut(HouseholdOut):
    members: list[HouseholdMemberOut] = []


class HouseholdInviteCreate(BaseModel):
    role: HouseholdRoleLiteral = "member"
    expires_in_days: int = Field(default=7, ge=1, le=30)


class HouseholdInviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    invite_code: str
    role: HouseholdRoleLiteral
    expires_at: datetime
    created_at: datetime


class HouseholdJoinRequest(BaseModel):
    invite_code: str = Field(min_length=6, max_length=32)


class ProductShareRequest(BaseModel):
    household_id: uuid.UUID | None = None
