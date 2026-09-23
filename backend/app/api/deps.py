"""Shared FastAPI dependencies: DB session, current user, pagination."""
import uuid

from fastapi import Depends, Query, Request
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import UnauthorizedError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header.")
    token = auth.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError("Invalid or expired access token.")
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise UnauthorizedError("Invalid token type.")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise UnauthorizedError("User no longer exists.")
    request.state.is_admin = bool(payload.get("is_admin", False))
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        from app.core.errors import ForbiddenError
        raise ForbiddenError("Admin access required.")
    return user


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
    ):
        self.page = page
        self.page_size = page_size