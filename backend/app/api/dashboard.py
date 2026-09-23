"""Today dashboard endpoint — the heart of OWNLY."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.analytics_events import AnalyticsEvent
from app.core.database import get_db
from app.integrations.analytics import track
from app.models import User
from app.services.dashboard_service import build_today_dashboard

router = APIRouter(tags=["dashboard"])
# `/today` is the canonical product-facing path; `/dashboard/today` stays for
# backward compatibility. Both call the exact same handler (no divergence).
alias_router = APIRouter(prefix="/today", tags=["dashboard"])


def _today_payload(db: Session, user: User):
    payload = build_today_dashboard(db, user.id)
    track(AnalyticsEvent.today_viewed, user.id, {"attention": len(payload.attention)})
    return payload


@router.get("/dashboard/today")
def today(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _today_payload(db, user)


alias_router.add_api_route("", today, methods=["GET"], name="today_alias")