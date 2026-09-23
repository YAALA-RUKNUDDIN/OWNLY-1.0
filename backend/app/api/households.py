import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.household import HouseholdRole
from app.models.user import User
from app.schemas.household import (
    HouseholdCreate,
    HouseholdDetailOut,
    HouseholdInviteCreate,
    HouseholdInviteOut,
    HouseholdJoinRequest,
    HouseholdOut,
    HouseholdUpdate,
)
from app.services.household_service import HouseholdService

router = APIRouter(prefix="/households", tags=["households"])


@router.post("", response_model=HouseholdOut, status_code=201)
def create_household(
    body: HouseholdCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HouseholdService(db)
    return service.create_household(user.id, body.name)


@router.get("", response_model=list[HouseholdOut])
def list_households(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HouseholdService(db)
    return service.list_user_households(user.id)


@router.post("/join", response_model=HouseholdDetailOut)
def join_household(
    body: HouseholdJoinRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HouseholdService(db)
    return service.join_household(user.id, body.invite_code)


@router.get("/{household_id}", response_model=HouseholdDetailOut)
def get_household(
    household_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HouseholdService(db)
    return service.get_household_detail(household_id, user.id)


@router.patch("/{household_id}", response_model=HouseholdDetailOut)
def update_household(
    household_id: uuid.UUID,
    body: HouseholdUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HouseholdService(db)
    return service.update_household(household_id, user.id, body.name)


@router.delete("/{household_id}", status_code=204)
def delete_household(
    household_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HouseholdService(db)
    service.delete_household(household_id, user.id)
    return None


@router.post("/{household_id}/invites", response_model=HouseholdInviteOut, status_code=201)
def create_invite(
    household_id: uuid.UUID,
    body: HouseholdInviteCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HouseholdService(db)
    role = HouseholdRole(body.role)
    invite = service.create_invite(household_id, user.id, role, body.expires_in_days)
    return HouseholdInviteOut(
        invite_code=invite.invite_code,
        role=invite.role.value,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.get("/{household_id}/invites", response_model=list[HouseholdInviteOut])
def list_invites(
    household_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HouseholdService(db)
    invites = service.list_active_invites(household_id, user.id)
    return [
        HouseholdInviteOut(
            invite_code=inv.invite_code,
            role=inv.role.value,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in invites
    ]


@router.delete("/{household_id}/members/{target_user_id}", status_code=204)
def remove_member(
    household_id: uuid.UUID,
    target_user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = HouseholdService(db)
    service.remove_member(household_id, user.id, target_user_id)
    return None
