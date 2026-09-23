"""OCR extraction endpoint.

Returns a DRAFT of extracted fields. Nothing is saved — the client must
present the draft to the user, who edits/confirms before creating a product
via POST /products. Extraction is best-effort and never guaranteed accurate.
"""
from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user
from app.core.analytics_events import AnalyticsEvent
from app.core.errors import ValidationError
from app.integrations.analytics import track
from app.integrations.ocr import get_ocr
from app.models import User

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/extract")
async def extract(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    data = await file.read()
    if not data:
        raise ValidationError("Empty file.", {"fields": {"file": "file is empty"}})
    if len(data) > 10 * 1024 * 1024:
        raise ValidationError("File too large (max 10 MB).", {"fields": {"file": "max size exceeded"}})
    if file.content_type and not file.content_type.startswith("image/"):
        raise ValidationError("OCR requires an image file (JPEG/PNG/HEIC/WebP).",
                              {"fields": {"file": "not an image"}})
    fields = get_ocr().extract(data, file.content_type or "image/jpeg")
    track(AnalyticsEvent.ocr_extracted, user.id, {"mime_type": file.content_type or "image/jpeg"})
    return {
        "draft": fields.to_dict(),
        "notice": "Extracted information is a best-effort draft. Please review and edit before saving.",
    }