"""Authentication endpoints: register, login, refresh (rotation + reuse
detection), logout (single device / all devices), me."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.datetime_utils import as_aware
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas.auth import (
    AuthResponse, LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest,
    TokenPair, UserOut,
)
from app.services.user_service import ensure_default_prefs

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_pair(db: Session, user: User, device_label: str | None = None) -> TokenPair:
    """Create an access token + a fresh refresh-token family (new login)."""
    access = create_access_token(str(user.id), user.is_admin)
    raw_refresh, refresh_hash = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        token_family=uuid.uuid4().hex,
        device_label=device_label,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.flush()
    return TokenPair(
        access_token=access,
        refresh_token=raw_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if existing:
        raise ConflictError("An account with this email already exists.")
    user = User(
        name=body.name.strip(),
        email=body.email.lower(),
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.flush()
    ensure_default_prefs(db, user.id)
    tokens = _issue_pair(db, user)
    db.commit()
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise UnauthorizedError("Incorrect email or password.")
    ensure_default_prefs(db, user.id)
    tokens = _issue_pair(db, user)
    db.commit()
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Rotate the refresh token. Reuse of a revoked token revokes the whole
    token family (theft detection)."""
    token_hash = hash_token(body.refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if not stored:
        raise UnauthorizedError("Invalid refresh token.")
    if stored.revoked:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_family == stored.token_family)
            .values(revoked=True)
        )
        db.commit()
        raise UnauthorizedError("Refresh token reuse detected. Please log in again.")
    if stored.expires_at and as_aware(stored.expires_at) < datetime.now(timezone.utc):
        raise UnauthorizedError("Refresh token expired. Please log in again.")

    stored.revoked = True
    user = db.get(User, stored.user_id)
    if not user:
        raise UnauthorizedError("User no longer exists.")
    access = create_access_token(str(user.id), user.is_admin)
    raw_new, new_hash = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        token_family=stored.token_family,
        device_label=stored.device_label,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()
    return TokenPair(
        access_token=access,
        refresh_token=raw_new,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(body.refresh_token)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if not stored:
        raise UnauthorizedError("Invalid refresh token.")
    if body.all_devices:
        db.execute(update(RefreshToken).where(RefreshToken.user_id == stored.user_id).values(revoked=True))
    else:
        stored.revoked = True
    db.commit()
    return {"message": "Logged out."}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user