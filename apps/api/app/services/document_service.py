import hashlib
import mimetypes
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.data_source import DataSource
from app.models.media import Document
from app.storage.base import Storage


def import_document(
    db: Session, storage: Storage, source_code: str, path: Path, document_code: str
) -> Document:
    source = db.scalar(select(DataSource).where(DataSource.source_code == source_code))
    if source is None:
        raise ValueError("Source does not exist")
    data = path.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    existing = db.scalar(
        select(Document).where(
            Document.source_id == source.id, Document.checksum_sha256 == checksum
        )
    )
    if existing:
        storage.store(existing.storage_key, data)
        return existing
    if db.scalar(select(Document.id).where(Document.document_code == document_code)):
        raise ValueError("Document code already represents a different file")
    key = f"documents/{checksum}"
    storage.store(key, data)
    document = Document(
        source_id=source.id,
        document_code=document_code,
        original_file_name=path.name,
        storage_key=key,
        mime_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        file_size=len(data),
        checksum_sha256=checksum,
    )
    db.add(document)
    db.flush()
    return document
