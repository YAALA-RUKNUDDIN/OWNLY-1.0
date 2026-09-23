"""Google Cloud Vision OCR provider (production). Requires
GOOGLE_VISION_API_KEY or Application Default Credentials."""
import base64
import re

import requests

from app.core.config import settings
from app.core.errors import OCRError
from app.integrations.ocr.base import ExtractedFields, OCRProvider
from app.integrations.ocr.tesseract import DATE_RE, INVOICE_RE, PRICE_RE


class GoogleVisionOCRProvider(OCRProvider):
    name = "google_vision"
    API_URL = "https://vision.googleapis.com/v1/images:annotate"

    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedFields:
        key = f"?key={settings.GOOGLE_VISION_API_KEY}" if settings.GOOGLE_VISION_API_KEY else ""
        body = {
            "requests": [{
                "image": {"content": base64.b64encode(image_bytes).decode()},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }]
        }
        try:
            resp = requests.post(self.API_URL + key, json=body, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            raise OCRError("Google Vision OCR request failed.", details={"error": str(e)})

        data = resp.json()
        try:
            annotation = data["responses"][0]["fullTextAnnotation"]
            raw = annotation["text"]
        except (KeyError, IndexError):
            raise OCRError("No readable text found in the document.")

        fields = ExtractedFields(provider=self.name, raw_text=raw, confidence=0.75)
        lines = [l.strip() for l in raw.splitlines() if l.strip()]

        for line in lines[:6]:
            if len(line) >= 4 and not any(k in line.lower() for k in ("invoice", "receipt", "bill", "tax", "date", "tel", "phone")):
                fields.product_name = line[:120]
                break

        for line in lines:
            if fields.price is None:
                m = PRICE_RE.search(line)
                if m:
                    fields.price = m.group(1).rstrip(".,")
            if fields.purchase_date is None:
                m = DATE_RE.search(line)
                if m:
                    fields.purchase_date = m.group(1)
            if fields.invoice_number is None:
                m = INVOICE_RE.search(line)
                if m:
                    fields.invoice_number = m.group(1)
        return fields