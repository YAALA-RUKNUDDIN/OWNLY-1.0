"""User profile, notification preferences, device tokens, data export,
account deletion."""
import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import ValidationError
from app.models import (
    DeviceToken, NotificationCategory, NotificationPreference, User,
)
from app.schemas.user import (
    DeviceTokenRequest, PrefsResponse, PrefsUpdateRequest, ProfileUpdate,
)
from app.services.user_service import ensure_default_prefs, get_prefs, parse_lead_days

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me")
def update_profile(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.name is not None:
        user.name = body.name.strip()[:120]
    if body.profile_image_url is not None:
        user.profile_image_url = body.profile_image_url[:500]
    db.add(user)
    db.commit()
    return {"id": user.id, "name": user.name, "email": user.email,
            "profile_image_url": user.profile_image_url}


@router.get("/me/prefs", response_model=PrefsResponse)
def get_notification_prefs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_default_prefs(db, user.id)
    db.commit()
    prefs = get_prefs(db, user.id)
    return {
        "preferences": [
            {"category": p.category.value, "enabled": p.enabled,
             "lead_days": parse_lead_days(p.lead_days)}
            for p in prefs
        ]
    }


@router.patch("/me/prefs", response_model=PrefsResponse)
def update_notification_prefs(
    body: PrefsUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_default_prefs(db, user.id)
    prefs = {p.category.value: p for p in get_prefs(db, user.id)}
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    for category, change in updates.items():
        if category not in NotificationCategory.__members__:
            raise ValidationError(f"Unknown notification category: {category}")
        pref = prefs[category]
        pref.enabled = change["enabled"]
        pref.lead_days = json.dumps(sorted(set(change["lead_days"]), reverse=True))
        db.add(pref)
    db.commit()
    return get_notification_prefs(user=user, db=db)


@router.post("/me/devices", status_code=201)
def register_device(
    body: DeviceTokenRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.scalar(select(DeviceToken).where(DeviceToken.fcm_token == body.fcm_token))
    if existing:
        if existing.user_id != user.id:
            existing.user_id = user.id
            existing.platform = body.platform
            db.commit()
            return {"message": "Device re-assigned."}
        return {"message": "Device already registered."}
    db.add(DeviceToken(user_id=user.id, fcm_token=body.fcm_token, platform=body.platform))
    db.commit()
    return {"message": "Device registered."}


@router.delete("/me/devices/{fcm_token}", status_code=204)
def unregister_device(
    fcm_token: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token_obj = db.scalar(
        select(DeviceToken).where(
            DeviceToken.fcm_token == fcm_token,
            DeviceToken.user_id == user.id,
        )
    )
    if token_obj:
        db.delete(token_obj)
        db.commit()
    return None


@router.get("/me/export")
def export_data(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full data export — users own their data."""
    from app.services.export_service import build_export
    return build_export(db, user.id)


@router.delete("/me", status_code=204)
def delete_account(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanent account deletion: cascades all products, documents (files
    physically removed from storage), tokens and preferences."""
    from app.integrations.storage import get_storage
    from app.models import Document

    docs = db.execute(select(Document).where(Document.user_id == user.id)).scalars().all()
    storage = get_storage()
    for doc in docs:
        try:
            storage.delete(doc.file_url)
        except Exception:
            pass
    db.delete(user)  # FK cascades remove all owned rows
    db.commit()
    return None