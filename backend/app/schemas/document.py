import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentTypeLiteral = Literal[
    "invoice", "receipt", "warranty_card", "insurance",
    "service_document", "repair_receipt", "manual", "other",
]


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    document_name: str
    document_type: DocumentTypeLiteral
    file_size: int
    mime_type: str
    created_at: datetime


class DocumentRename(BaseModel):
    document_name: str = Field(min_length=1, max_length=255)


class DocumentDownloadOut(BaseModel):
    download_url: str
    expires_in_seconds: int