"""OCR provider factory — selected by OCR_PROVIDER env var.

Imports are lazy so the API can start without OCR libraries installed
(OCR endpoints return a clear error until Tesseract/Google Vision deps
are available).
"""
from functools import lru_cache

from app.core.config import settings
from app.core.errors import OCRError
from app.integrations.ocr.base import OCRProvider


@lru_cache
def get_ocr() -> OCRProvider:
    if settings.OCR_PROVIDER == "google_vision":
        try:
            from app.integrations.ocr.google_vision import GoogleVisionOCRProvider
        except ImportError as e:
            raise OCRError(
                "Google Vision OCR is not available. Install google-cloud-vision "
                "and requests, or set OCR_PROVIDER=tesseract.",
                details={"error": str(e)},
            )
        return GoogleVisionOCRProvider()
    try:
        from app.integrations.ocr.tesseract import TesseractOCRProvider
    except ImportError as e:
        raise OCRError(
            "Tesseract OCR is not available on this machine. Install the "
            "Tesseract engine + 'pip install pytesseract Pillow', or set "
            "OCR_PROVIDER=google_vision.",
            details={"error": str(e)},
        )
    return TesseractOCRProvider()