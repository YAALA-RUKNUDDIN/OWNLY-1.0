"""Authenticated local-file serving endpoint (used by LocalStorageProvider's
signed URLs). Verifies HMAC signature + expiry — no database hit needed."""
import base64
import hashlib
import hmac
import time

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.core.config import settings
from app.core.errors import NotFoundError, UnauthorizedError
from app.integrations.storage import get_storage

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{key_b64}")
def serve_file(key_b64: str, exp: int, sig: str, request: Request):
    if time.time() > exp:
        raise UnauthorizedError("Signed URL expired.")
    key = base64.urlsafe_b64decode(key_b64.encode()).decode()
    expected = hmac.new(
        settings.JWT_SECRET.encode(), f"{key}:{exp}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise UnauthorizedError("Invalid signature.")
    try:
        data = get_storage().get(key)
    except NotFoundError:
        raise
    mime = "application/octet-stream"
    if key.endswith(".pdf"):
        mime = "application/pdf"
    elif key.endswith((".jpg", ".jpeg")):
        mime = "image/jpeg"
    elif key.endswith(".png"):
        mime = "image/png"
    elif key.endswith(".webp"):
        mime = "image/webp"
    return Response(content=data, media_type=mime, headers={"Cache-Control": "private, max-age=300"})