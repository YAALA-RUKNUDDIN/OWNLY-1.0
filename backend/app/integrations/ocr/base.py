"""OCR provider abstraction.

The application never depends on a specific OCR vendor. Providers return a
DRAFT of extracted fields — the API always presents this to the user for
editing/confirmation before anything is saved. Extraction is best-effort and
never guaranteed accurate (this is communicated to users in the UI).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractedFields:
    """Draft extraction result. All fields optional; user confirms/edits."""
    product_name: str | None = None
    brand: str | None = None
    model: str | None = None
    purchase_date: str | None = None      # ISO date string if found
    price: str | None = None
    currency: str | None = None
    seller: str | None = None
    invoice_number: str | None = None
    warranty_text: str | None = None
    confidence: float = 0.0               # 0..1 overall confidence
    raw_text: str = ""                    # full OCR text for user reference
    provider: str = ""

    def to_dict(self) -> dict:
        return {
            "product_name": self.product_name,
            "brand": self.brand,
            "model": self.model,
            "purchase_date": self.purchase_date,
            "price": self.price,
            "currency": self.currency,
            "seller": self.seller,
            "invoice_number": self.invoice_number,
            "warranty_text": self.warranty_text,
            "confidence": round(self.confidence, 2),
            "raw_text": self.raw_text,
            "provider": self.provider,
        }


class OCRProvider(ABC):
    name: str = "base"

    @abstractmethod
    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedFields:
        """Run OCR + field extraction. Raises OCRError on failure."""