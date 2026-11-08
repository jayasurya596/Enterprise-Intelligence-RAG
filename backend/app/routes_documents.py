import logging
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.embeddings import get_embeddings
from app.models import Chunk, Document, User
from app.parsing import chunk_pages, extract_text, validate_file
from app.schemas import DocumentOut
from app.security import get_current_user
from app.vector_index import get_vector_index

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


def _out(document: Document) -> DocumentOut:
    return DocumentOut(id=document.id, source_name=document.source_name, content_type=document.content_type, byte_size=document.byte_size, status=document.status, error_summary=document.error_summary, domain_labels=document.domain_labels or [], created_at=document.created_at, chunk_count=len(document.chunks))


def _safe_filename(name: str) -> str:
    basename = Path(name.replace("\\", "/")).name
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", basename).strip()
    return cleaned[:255] or "uploaded-document"


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), domains: str = Form(default=""), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        suffix, content_type = validate_file(file.filename or "", content, settings.max_upload_mb)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    requested_labels = [label.strip()[:80] for label in domains.split(",") if label.strip()]
    if not requested_labels and settings.default_domain.strip():
        requested_labels = [settings.default_domain.strip()[:80]]
    labels = list(dict.fromkeys(requested_labels))[:30]
    storage_name = f"{uuid4().hex}{suffix}"
    storage_dir = settings.upload_dir.resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / storage_name
    document = Document(owner_id=user.id, organization_id=user.organization_id, source_name=_safe_filename(file.filename or "uploaded-document"), storage_name=storage_name, content_type=content_type, byte_size=len(content), status="processing", domain_labels=labels)
    db.add(document)
    db.commit()
    db.refresh(document)
    try:
        storage_path.write_bytes(content)
        pages = extract_text(storage_path, suffix)
        parts = chunk_pages(pages, settings.chunk_size_chars, settings.chunk_overlap_chars)
        records = [Chunk(document_id=document.id, owner_id=user.id, organization_id=user.organization_id, chunk_order=index, page_number=part.page_number, domain_labels=labels, content=part.text) for index, part in enumerate(parts)]
        db.add_all(records)
        db.commit()
        vectors = get_embeddings().embed_many([part.content for part in records])
        payloads = [{"id": part.id, "owner_id": user.id, "organization_id": user.organization_id, "document_id": document.id, "source_name": document.source_name, "page_number": part.page_number, "chunk_order": part.chunk_order, "domain_labels": labels} for part in records]
        get_vector_index().upsert(payloads, vectors)
        document.status = "ready"
        document.error_summary = None
        db.commit()
        db.refresh(document)
        return _out(document)
    except Exception as exc:
        logger.exception("Document ingestion failed for document %s", document.id)
        db.rollback()
        try:
            get_vector_index().delete_document(document.id, user.id)
        except Exception:
            logger.warning("Best-effort vector cleanup failed for %s", document.id)
        db.query(Chunk).filter(Chunk.document_id == document.id, Chunk.owner_id == user.id).delete(synchronize_session=False)
        document = db.get(Document, document.id)
        if document:
            document.status = "failed"
            document.error_summary = (str(exc) if isinstance(exc, ValueError) else "Document processing failed. Check service configuration and retry.")[:300]
        db.commit()
        storage_path.unlink(missing_ok=True)
        if isinstance(exc, ValueError):
            return _out(document)
        if not document:
            raise HTTPException(status_code=500, detail="Document processing failed.") from exc
        return _out(document)


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    documents = db.scalars(select(Document).where(Document.owner_id == user.id).order_by(Document.created_at.desc())).all()
    return [_out(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return _out(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    try:
        get_vector_index().delete_document(document.id, user.id)
        (settings.upload_dir.resolve() / document.storage_name).unlink(missing_ok=True)
        db.delete(document)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Document deletion failed for %s", document_id)
        raise HTTPException(status_code=503, detail="Document cleanup did not complete. Retry later.") from exc
    return None

