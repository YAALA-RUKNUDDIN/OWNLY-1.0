"""Google Cloud Vision OCR provider (production).

Supports both:
1. API Key authentication (GOOGLE_VISION_API_KEY)
2. Service Account / Application Default Credentials (ADC) OAuth2 bearer tokens
   (via GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CREDENTIALS_JSON, or google.auth.default).
"""
import base64
import json
import os
import re
from datetime import datetime
from typing import Any

import requests

from app.core.config import settings
from app.core.errors import OCRError
from app.integrations.ocr.base import ExtractedFields, OCRProvider

# Comprehensive date patterns
ISO_DATE_RE = re.compile(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b")
SLASH_DATE_RE = re.compile(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b")
TEXT_DATE_RE = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2}),?\s+(\d{4})\b",
    re.IGNORECASE,
)

# Price and money patterns
TOTAL_RE = re.compile(
    r"(?:total|amount\s+due|balance\s+due|grand\s+total)\s*[:=]?\s*[$€£¥₹]?\s*(\d+[.,]\d{2})",
    re.IGNORECASE,
)
PRICE_GENERIC_RE = re.compile(
    r"(?:[$€£¥₹]\s*(\d+[.,]\d{2})|(\d+[.,]\d{2})\s*(?:USD|EUR|GBP|INR))",
    re.IGNORECASE,
)

# Invoice / order number
INVOICE_PATTERN = re.compile(
    r"(?:invoice|receipt|order|trans(?:action)?|bill)\s*(?:#|no\.?|num\.?|id)?\s*[:=]?\s*([A-Z0-9-]{4,30})",
    re.IGNORECASE,
)

EXCLUDED_HEADER_WORDS = (
    "invoice", "receipt", "tax invoice", "bill", "customer", "cashier",
    "register", "terminal", "welcome", "thank you", "tel:", "phone:", "fax:",
    "address", "www.", "http", "store #", "trans #"
)


class GoogleVisionOCRProvider(OCRProvider):
    name = "google_vision"
    API_URL = "https://vision.googleapis.com/v1/images:annotate"

    def __init__(self, api_key: str | None = None, credentials_json: str | None = None, credentials_path: str | None = None):
        self.api_key = api_key if api_key is not None else settings.GOOGLE_VISION_API_KEY
        self.credentials_json = credentials_json if credentials_json is not None else settings.GOOGLE_CREDENTIALS_JSON
        self.credentials_path = (
            credentials_path
            or settings.GOOGLE_APPLICATION_CREDENTIALS
            or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        )
        self._oauth_creds: Any = None

    def _get_auth_headers_and_url(self) -> tuple[dict[str, str], str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            return headers, f"{self.API_URL}?key={self.api_key}"

        # If no API key, attempt OAuth2 service account authentication
        token = self._get_oauth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            return headers, self.API_URL

        # If neither provided, still try direct call in case running in authorized environment
        return headers, self.API_URL

    def _get_oauth_token(self) -> str | None:
        try:
            from google.auth.transport.requests import Request as GoogleAuthRequest
            from google.oauth2 import service_account
            import google.auth
        except ImportError:
            return None

        if self._oauth_creds is None:
            scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            if self.credentials_json:
                info = json.loads(self.credentials_json)
                self._oauth_creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
            elif self.credentials_path and os.path.exists(self.credentials_path):
                self._oauth_creds = service_account.Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
            else:
                try:
                    self._oauth_creds, _ = google.auth.default(scopes=scopes)
                except Exception:
                    self._oauth_creds = None

        if self._oauth_creds:
            from google.auth.transport.requests import Request as GoogleAuthRequest
            if not self._oauth_creds.valid:
                self._oauth_creds.refresh(GoogleAuthRequest())
            return self._oauth_creds.token

        return None

    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedFields:
        headers, url = self._get_auth_headers_and_url()
        b64_content = base64.b64encode(image_bytes).decode("utf-8")
        body = {
            "requests": [{
                "image": {"content": b64_content},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }]
        }

        try:
            resp = requests.post(url, json=body, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise OCRError("Google Vision OCR request failed.", details={"error": str(e)})

        data = resp.json()
        responses = data.get("responses", [])
        if not responses:
            raise OCRError("Empty response received from Google Vision OCR.")

        first_resp = responses[0]
        if "error" in first_resp:
            err_details = first_resp["error"]
            msg = err_details.get("message", "Vision API error")
            raise OCRError(f"Google Vision API error: {msg}", details=err_details)

        annotation = first_resp.get("fullTextAnnotation")
        if not annotation or not annotation.get("text"):
            raise OCRError("No readable text found in the document.")

        raw_text = annotation["text"]
        return self._parse_receipt_text(raw_text)

    def _parse_receipt_text(self, raw: str) -> ExtractedFields:
        fields = ExtractedFields(provider=self.name, raw_text=raw)
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            return fields

        # 1. Identify Seller / Merchant (typically in first 3 non-excluded lines)
        for line in lines[:5]:
            lower = line.lower()
            if len(line) >= 3 and not any(term in lower for term in EXCLUDED_HEADER_WORDS):
                fields.seller = line[:120]
                break

        # 2. Identify Product Name Candidate (first substantive line after seller)
        for line in lines:
            lower = line.lower()
            if line == fields.seller:
                continue
            if len(line) >= 4 and not any(term in lower for term in EXCLUDED_HEADER_WORDS):
                if not re.search(r"^\d+[\s\-/.]", line) and not TOTAL_RE.search(line):
                    fields.product_name = line[:120]
                    break

        # Fallback product name to seller or first line if none found
        if not fields.product_name and lines:
            fields.product_name = lines[0][:120]

        # 3. Price / Total extraction
        # Prefer explicit "TOTAL" line
        for line in reversed(lines):
            total_match = TOTAL_RE.search(line)
            if total_match:
                fields.price = total_match.group(1).replace(",", ".")
                break

        # Fallback to general price regex from bottom up
        if not fields.price:
            for line in reversed(lines):
                m = PRICE_GENERIC_RE.search(line)
                if m:
                    fields.price = (m.group(1) or m.group(2)).replace(",", ".")
                    break

        # Currency detection
        if any(sym in raw for sym in ("$", "USD")):
            fields.currency = "USD"
        elif any(sym in raw for sym in ("€", "EUR")):
            fields.currency = "EUR"
        elif any(sym in raw for sym in ("£", "GBP")):
            fields.currency = "GBP"
        elif any(sym in raw for sym in ("₹", "INR")):
            fields.currency = "INR"

        # 4. Purchase date extraction
        # Try ISO first (YYYY-MM-DD)
        iso_m = ISO_DATE_RE.search(raw)
        if iso_m:
            fields.purchase_date = iso_m.group(1).replace("/", "-")
        else:
            text_m = TEXT_DATE_RE.search(raw)
            if text_m:
                month_str, day_str, year_str = text_m.groups()
                try:
                    dt = datetime.strptime(f"{month_str[:3]} {day_str} {year_str}", "%b %d %Y")
                    fields.purchase_date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    fields.purchase_date = f"{year_str}-{month_str}-{day_str}"
            else:
                slash_m = SLASH_DATE_RE.search(raw)
                if slash_m:
                    fields.purchase_date = slash_m.group(1).replace("/", "-")

        # 5. Invoice / Order number extraction
        for line in lines:
            inv_m = INVOICE_PATTERN.search(line)
            if inv_m:
                fields.invoice_number = inv_m.group(1)
                break

        # 6. Confidence calculation
        score = 0.40  # baseline for readable document
        if fields.product_name:
            score += 0.20
        if fields.price:
            score += 0.15
        if fields.purchase_date:
            score += 0.15
        if fields.invoice_number or fields.seller:
            score += 0.10
        fields.confidence = min(0.98, round(score, 2))

        return fields