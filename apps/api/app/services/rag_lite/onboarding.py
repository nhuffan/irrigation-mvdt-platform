"""Guarded local document onboarding; no review promotion, implicit authorization or SQL edits on dry-run."""

import io
import json
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from pypdf import PdfReader
from sqlalchemy import select

from app.models.asset import Asset
from app.models.data_source import DataSource
from app.models.media import Document
from app.services.rag_lite.indexer import (
    MAX_BYTES,
    MAX_PAGES,
    VERSION,
    atomic_json,
    digest,
    extract,
    load_allowlist,
    load_index,
)
from app.services.rag_lite.retriever import source_scopes
from app.services.rag_lite.sections import extract_sections, scoped_chunks


def prepare(db, storage, settings, entries, authorization_reference=None):
    """Validate the whole selection and extract in memory before mutating anything."""
    authorization = load_allowlist(settings.rag_lite_allowlist_path)
    prepared, identities, hashes = [], set(), set()
    for entry in entries:
        path = Path(entry["file"]).resolve()
        if not path.is_file():
            raise ValueError(f"FILE_UNAVAILABLE: {path.name}")
        if path.suffix.lower() != ".pdf" or not 0 < path.stat().st_size <= MAX_BYTES:
            raise ValueError("PDF_TYPE_OR_SIZE_LIMIT")
        data = path.read_bytes()
        checksum = digest(data)
        if entry.get("checksum_sha256") and entry["checksum_sha256"] != checksum:
            raise ValueError("ORIGINAL_CHECKSUM_MISMATCH")
        if not data.startswith(b"%PDF-"):
            raise ValueError("PDF_SIGNATURE_INVALID")
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted or not 0 < len(reader.pages) <= MAX_PAGES:
            raise ValueError("ENCRYPTED_OR_PAGE_COUNT_LIMIT")
        source = db.scalar(
            select(DataSource).where(DataSource.source_code == entry["source_code"])
        )
        if source is None or source.verification_status == "REJECTED":
            raise ValueError("EXISTING_NON_REJECTED_SOURCE_REQUIRED")
        allowed_assets = set(
            source_scopes(db, source.reservoir_id).get(str(source.id), [])
        )
        requested = {str(UUID(v)) for v in entry["asset_ids"]}
        if not requested or not requested <= allowed_assets:
            raise ValueError("REVIEWED_DIRECT_SOURCE_ASSET_LINK_REQUIRED")
        for asset_id in requested:
            asset = db.get(Asset, UUID(asset_id))
            if not asset or asset.reservoir_id != source.reservoir_id:
                raise ValueError("RESERVOIR_ASSET_MISMATCH")
        sections = entry.get("sections", [])
        if any(not set(s["asset_ids"]) <= requested for s in sections):
            raise ValueError("SECTION_OUTSIDE_SELECTED_ASSETS")
        # Multi-asset documents require actual section boundaries. No entire-report attribution.
        if len(allowed_assets) > 1 and not sections:
            raise ValueError("MULTI_ASSET_SOURCE_REQUIRES_SECTIONS")
        code = entry["document_code"].strip()
        if not code or len(code) > 100 or code in identities or checksum in hashes:
            raise ValueError("DUPLICATE_OR_INVALID_SELECTION")
        identities.add(code)
        hashes.add(checksum)
        existing = db.scalar(
            select(Document).where(
                Document.source_id == source.id, Document.checksum_sha256 == checksum
            )
        )
        by_code = db.scalar(select(Document).where(Document.document_code == code))
        if by_code is not existing or (existing and existing.document_code != code):
            raise ValueError("DOCUMENT_IDENTITY_CONFLICT")
        doc = existing or Document(
            id=uuid5(NAMESPACE_URL, f"rag-lite:{source.id}:{checksum}"),
            source_id=source.id,
            document_code=code,
            original_file_name=path.name,
            storage_key=f"documents/{checksum}",
            mime_type="application/pdf",
            file_size=len(data),
            page_count=len(reader.pages),
            checksum_sha256=checksum,
        )
        if existing:
            if (
                existing.file_size != len(data)
                or existing.mime_type != "application/pdf"
                or (
                    existing.page_count is not None
                    and existing.page_count != len(reader.pages)
                )
            ):
                raise ValueError("EXISTING_METADATA_CONFLICT")
            stored = storage.path(existing.storage_key)
            if not stored.is_file() or digest(stored.read_bytes()) != checksum:
                raise ValueError("EXISTING_ORIGINAL_MISSING_OR_CHANGED")
        if authorization.get(str(doc.id)) != checksum and not authorization_reference:
            raise ValueError("EXPLICIT_LOCAL_INDEX_AUTHORIZATION_REQUIRED")
        index = (
            extract_sections(doc, data, sections, entry.get("scope_review", ""))
            if sections
            else extract(doc, data)
        )
        target = settings.rag_lite_index_dir / f"{doc.id}.json"
        try:
            prior = load_index(target, doc)
            unchanged = prior == index
        except (OSError, ValueError, KeyError, TypeError):
            unchanged = False
        prepared.append((doc, existing is None, data, index, unchanged, requested))
    if not prepared:
        raise ValueError("NO_SELECTED_DOCUMENTS")
    return prepared


def outcome(prepared, applied):
    return {
        "applied": applied,
        "documents": [
            {
                "document_id": str(doc.id),
                "document_code": doc.document_code,
                "source_id": str(doc.source_id),
                "original_file_name": doc.original_file_name,
                "checksum_sha256": doc.checksum_sha256,
                "status": "IMPORTED"
                if new and applied
                else "WOULD_IMPORT"
                if new
                else "SKIPPED"
                if unchanged
                else "REINDEXED"
                if applied
                else "WOULD_REINDEX",
                "asset_ids": sorted(ids),
                "page_count": index["page_count"],
                "searchable_pages": len({c["page"] for c in index["chunks"]}),
                "chunks": len(index["chunks"]),
                "asset_coverage": {
                    a: {
                        "pages": len({c["page"] for c in scoped_chunks(index, a)}),
                        "chunks": len(scoped_chunks(index, a)),
                    }
                    for a in sorted(ids)
                },
                "new_reviewed_fields": [],
                "source_verification": "UNCHANGED",
            }
            for doc, new, _, index, unchanged, ids in prepared
        ],
        "blockers": [],
    }


def apply_prepared(db, storage, settings, prepared, authorization_reference=None):
    """Replace only selected caches/manifest entries; restore them if commit fails."""
    allow_path = settings.rag_lite_allowlist_path
    if allow_path is None:
        raise ValueError("ALLOWLIST_PATH_REQUIRED")
    try:
        allow = json.loads(allow_path.read_text())
        if allow.get("version") != 1 or not allow.get("authorization"):
            raise ValueError("INVALID_AUTHORIZATION_FILE")
    except (OSError, ValueError):
        raise ValueError("VALID_EXISTING_AUTHORIZATION_FILE_REQUIRED") from None
    manifest_path = settings.rag_lite_index_dir / "rag_corpus_manifest.json"
    manifest = (
        json.loads(manifest_path.read_text())
        if manifest_path.exists()
        else {"version": VERSION, "documents": []}
    )
    replacements, backups, created_originals = {}, {}, {}
    try:
        for doc, new, data, index, unchanged, ids in prepared:
            if new:
                db.add(doc)
            path = storage.path(doc.storage_key)
            if path.exists():
                if digest(path.read_bytes()) != doc.checksum_sha256:
                    raise ValueError("STORAGE_CONTENT_CONFLICT")
            else:
                storage.store(doc.storage_key, data)
                created_originals[doc.storage_key] = (path, doc.checksum_sha256)
            if not unchanged:
                replacements[settings.rag_lite_index_dir / f"{doc.id}.json"] = index
            row = next(
                (r for r in allow["documents"] if r["document_id"] == str(doc.id)), None
            )
            if row is None:
                if not authorization_reference:
                    raise ValueError("EXPLICIT_LOCAL_INDEX_AUTHORIZATION_REQUIRED")
                row = {
                    "document_id": str(doc.id),
                    "checksum_sha256": doc.checksum_sha256,
                    "authorization_reference": authorization_reference,
                }
                allow["documents"].append(row)
            if row["checksum_sha256"] != doc.checksum_sha256:
                raise ValueError("AUTHORIZATION_CHECKSUM_CONFLICT")
            if index.get("scope_sha256"):
                row["scope_sha256"] = index["scope_sha256"]
            elif row.get("scope_sha256"):
                raise ValueError("CANNOT_SILENTLY_REMOVE_SECTION_SCOPE")
            old_entry = next(
                (r for r in manifest["documents"] if r["document_id"] == str(doc.id)),
                None,
            )
            item = dict(old_entry or {})
            item.update(
                document_id=str(doc.id),
                source_id=str(doc.source_id),
                checksum_sha256=doc.checksum_sha256,
                asset_ids=sorted(ids),
                admissible=bool(index["chunks"]),
                status="INDEXED" if index["chunks"] else "NO_EXTRACTABLE_TEXT",
                page_count=index["page_count"],
                text_pages=sum(p["indexed"] for p in index["coverage"]),
                characters=sum(p["characters"] for p in index["coverage"]),
                chunk_count=len(index["chunks"]),
            )
            if old_entry is not None:
                manifest["documents"][manifest["documents"].index(old_entry)] = item
            else:
                manifest["documents"].append(item)
        db.flush()
        replacements[manifest_path] = manifest
        replacements[allow_path] = (
            allow  # Authorization is written last: failures close access.
        )
        backups.update(
            {p: p.read_bytes() if p.exists() else None for p in replacements}
        )
        for path, value in replacements.items():
            if not path.exists() or json.loads(path.read_text()) != value:
                atomic_json(path, value)
        db.commit()
    except Exception:
        db.rollback()
        for path, data in backups.items():
            if data is None:
                path.unlink(missing_ok=True)
            else:
                from tempfile import NamedTemporaryFile

                with NamedTemporaryFile(dir=path.parent, delete=False) as temp:
                    temp.write(data)
                    temporary = Path(temp.name)
                temporary.replace(path)
        for key, (path, checksum) in created_originals.items():
            # A shared original may have acquired another committed document link.
            # Preserve preexisting files, referenced files and any changed bytes.
            referenced = db.scalar(
                select(Document.id).where(Document.storage_key == key).limit(1)
            )
            if (
                referenced is None
                and path.is_file()
                and digest(path.read_bytes()) == checksum
            ):
                path.unlink()
        raise
