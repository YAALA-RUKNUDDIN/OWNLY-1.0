"""Local Tesseract OCR provider (free, no API key). Requires the
Tesseract binary; see .env.example for TESSERACT_CMD."""
import re
from datetime import datetime

import pytesseract
from PIL import Image
import io

from app.core.config import settings
from app.core.errors import OCRError
from app.integrations.ocr.base import ExtractedFields, OCRProvider

PRICE_RE = re.compile(r"(?:total|amount|price|rs\.?|₹|\$|€|£)\s*:?\s*([0-9][0-9,., ]*)", re.IGNORECASE)
DATE_RE = re.compile(r"(\d{1,4}[./-]\d{1,2}[./-]\d{1,4})")
INVOICE_RE = re.compile(r"(?:invoice|receipt|bill)\s*(?:no\.?|number|#)\s*:?\s*([A-Z0-9-]{3,})", re.IGNORECASE)


class TesseractOCRProvider(OCRProvider):
    name = "tesseract"

    def __init__(self):
        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedFields:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            raw = pytesseract.image_to_string(image)
        except Exception as e:
            raise OCRError(
                "OCR processing failed. Make sure Tesseract is installed and the file is a valid image.",
                details={"error": str(e)},
            )
        if not raw.strip():
            raise OCRError("No readable text found in the image. Try a clearer photo.")

        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        fields = ExtractedFields(provider=self.name, raw_text=raw, confidence=0.5)

        # Product name: first substantial line, skipping store-header noise
        for line in lines[:6]:
            if len(line) >= 4 and not any(k in line.lower() for k in ("invoice", "receipt", "bill", "tax", "date", "tel", "phone", "www")):
                fields.product_name = line[:120]
                break

        for line in lines:
            if fields.seller is None and any(k in line.lower() for k in ("store", "shop", "seller", "sold by")):
                fields.seller = line.split(":")[-1].strip()[:120] or line[:120]
            if fields.price is None:
                m = PRICE_RE.search(line)
                if m:
                    fields.price = m.group(1).strip().rstrip(".,")
            if fields.purchase_date is None:
                m = DATE_RE.search(line)
                if m:
                    fields.purchase_date = self._normalize_date(m.group(1))
            if fields.invoice_number is None:
                m = INVOICE_RE.search(line)
                if m:
                    fields.invoice_number = m.group(1)

        if fields.price:
            fields.confidence = min(0.85, fields.confidence + 0.15)
        if fields.purchase_date:
            fields.confidence = min(0.9, fields.confidence + 0.1)
        return fields

    @staticmethod
    def _normalize_date(text: str) -> str | None:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%m/%d/%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                return datetime.strptime(text.strip(), fmt).date().isoformat()
            except ValueError:
                continue
        return text