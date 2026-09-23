"""Today dashboard endpoint — the heart of OWNLY."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.services.dashboard_service import build_today_dashboard

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/today")
def today(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_today_dashboard(db, user.id)