"""Document upload/download/rename/delete with validation and signed URLs."""
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.analytics_events import AnalyticsEvent
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import NotFoundError, StorageError, ValidationError
from app.integrations.analytics import track
from app.integrations.storage import get_storage
from app.models import Document, DocumentType, EventType, User
from app.repositories.document_repo import DocumentRepository
from app.repositories.product_repo import ProductRepository
from app.schemas.document import DocumentDownloadOut, DocumentOut, DocumentRename
from app.services.timeline_service import record_event

router = APIRouter(tags=["documents"])

# Magic-byte signatures for upload validation
MAGIC = {
    b"%PDF": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
}


def _validate_upload(file: UploadFile, data: bytes) -> str:
    if len(data) > settings.max_upload_bytes:
        raise ValidationError(
            f"File too large. Maximum {settings.MAX_UPLOAD_SIZE_MB} MB.",
            {"fields": {"file": "max size exceeded"}},
        )
    if len(data) == 0:
        raise ValidationError("Empty file.", {"fields": {"file": "file is empty"}})
    detected = next((v for k, v in MAGIC.items() if data.startswith(k)), None)
    if detected is None:
        # Allow webp/heic by declared mime type as fallback
        if file.content_type not in settings.allowed_doc_types_list:
            raise ValidationError(
                "Unsupported file type. Allowed: PDF, JPEG, PNG, HEIC, WebP.",
                {"fields": {"file": "unsupported type"}},
            )
        return file.content_type
    if detected not in settings.allowed_doc_types_list:
        raise ValidationError("File type not allowed.", {"fields": {"file": "unsupported type"}})
    return detected


@router.post("/products/{product_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    document_name: str = Form(...),
    document_type: DocumentType = Form(DocumentType.other),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = ProductRepository(db, user.id).get(product_id)
    if not product:
        raise NotFoundError("Product not found.")

    data = await file.read()
    mime = _validate_upload(file, data)

    storage = get_storage()
    key = f"users/{user.id}/products/{product_id}/{uuid.uuid4().hex}_{file.filename}"
    try:
        storage.upload(key, data, mime)
    except Exception as e:
        raise StorageError("Failed to store the file. Please try again.", {"error": str(e)})

    doc = Document(
        product_id=product_id,
        user_id=user.id,
        document_name=document_name.strip()[:255],
        document_type=document_type,
        file_url=key,
        file_size=len(data),
        mime_type=mime,
    )
    db.add(doc)
    db.flush()
    record_event(
        db, product_id,
        EventType.invoice_uploaded if document_type == DocumentType.invoice else EventType.document_uploaded,
        title=f"{document_type.replace('_', ' ').title()} added",
        description=document_name.strip()[:200],
    )
    db.commit()
    db.refresh(doc)
    track(AnalyticsEvent.document_uploaded, user.id, {"document_type": document_type.value})
    return doc


@router.get("/products/{product_id}/documents", response_model=list[DocumentOut])
def list_documents(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = ProductRepository(db, user.id).get(product_id)
    if not product:
        raise NotFoundError("Product not found.")
    from app.repositories.document_repo import DocumentRepository
    return DocumentRepository(db, user.id).list_for_product(product_id)


@router.get("/documents/{document_id}/download", response_model=DocumentDownloadOut)
def download_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = DocumentRepository(db, user.id).get(document_id)
    if not doc:
        raise NotFoundError("Document not found.")
    url = get_storage().signed_url(doc.file_url, expires_in_seconds=600)
    return {"download_url": url, "expires_in_seconds": 600}


@router.patch("/documents/{document_id}", response_model=DocumentOut)
def rename_document(
    document_id: uuid.UUID,
    body: DocumentRename,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = DocumentRepository(db, user.id).get(document_id)
    if not doc:
        raise NotFoundError("Document not found.")
    doc.document_name = body.document_name.strip()[:255]
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = DocumentRepository(db, user.id).get(document_id)
    if not doc:
        raise NotFoundError("Document not found.")
    try:
        get_storage().delete(doc.file_url)  # permanent deletion — privacy first
    except Exception:
        pass  # storage object may already be gone; DB record still removed
    db.delete(doc)
    db.commit()
    return None