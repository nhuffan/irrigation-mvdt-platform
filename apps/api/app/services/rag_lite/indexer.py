"""Deterministic page-first JSON cache outside canonical tables; never writes SQL."""

import hashlib
import io
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from pypdf import PdfReader
from pypdf.errors import PdfReadError

VERSION = "rag-lite-page-keyword-v1"
CHUNK_CHARS = 1400
MAX_BYTES = 25 * 1024 * 1024
MAX_PAGES = 300


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_pdf(storage, doc) -> bytes:
    path = storage.path(doc.storage_key)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("DOCUMENT_SIZE_LIMIT")
    data = path.read_bytes()
    if not doc.checksum_sha256 or digest(data) != doc.checksum_sha256:
        raise ValueError("CHECKSUM_MISMATCH")
    return data


def chunks_for_page(document_id: str, checksum: str, page: int, text: str):
    normalized = re.sub(r"\s+", " ", text).strip()
    # Short/image-only pages are not useful evidence. No OCR or invented text.
    if len(normalized) < 40:
        return []
    result = []
    for offset in range(0, len(normalized), CHUNK_CHARS):
        excerpt = normalized[offset : offset + CHUNK_CHARS]
        chunk_hash = digest(excerpt.encode())
        identity = f"{VERSION}:{document_id}:{checksum}:{page}:{offset}:{chunk_hash}"
        result.append(
            {
                "chunk_id": digest(identity.encode()),
                "page": page,
                "offset": offset,
                "text": excerpt,
                "sha256": chunk_hash,
            }
        )
    return result


def extract(doc, data: bytes):
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("ENCRYPTED_PDF")
    if not 0 < len(reader.pages) <= MAX_PAGES:
        raise ValueError("PAGE_COUNT_LIMIT")
    chunks, coverage = [], []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        pieces = chunks_for_page(str(doc.id), doc.checksum_sha256, number, text)
        coverage.append(
            {"page": number, "characters": len(text.strip()), "indexed": bool(pieces)}
        )
        chunks.extend(pieces)
    return {
        "version": VERSION,
        "document_id": str(doc.id),
        "source_id": str(doc.source_id),
        "checksum_sha256": doc.checksum_sha256,
        "page_count": len(reader.pages),
        "coverage": coverage,
        "chunks": chunks,
    }


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w", dir=path.parent, delete=False, encoding="utf-8"
    ) as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        temp = Path(f.name)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def load_allowlist(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    try:
        value = json.loads(path.read_text())
        if value.get("version") != 1 or not value.get("authorization"):
            return {}
        from uuid import UUID

        return {
            str(UUID(row["document_id"])): row["checksum_sha256"]
            for row in value["documents"]
            if re.fullmatch(r"[0-9a-f]{64}", row["checksum_sha256"])
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}


def load_index(path: Path, doc):
    value = json.loads(path.read_text())
    if (
        value["version"] != VERSION
        or value["document_id"] != str(doc.id)
        or value["source_id"] != str(doc.source_id)
        or value["checksum_sha256"] != doc.checksum_sha256
        or not 0 < value["page_count"] <= MAX_PAGES
    ):
        raise ValueError("STALE_INDEX")
    for chunk in value["chunks"]:
        if not 1 <= chunk["page"] <= value["page_count"]:
            raise ValueError("INVALID_PAGE")
        identity = f"{VERSION}:{doc.id}:{doc.checksum_sha256}:{chunk['page']}:{chunk['offset']}:{chunk['sha256']}"
        if (
            digest(chunk["text"].encode()) != chunk["sha256"]
            or digest(identity.encode()) != chunk["chunk_id"]
            or len(chunk["text"]) > CHUNK_CHARS
        ):
            raise ValueError("INVALID_CHUNK")
    return value


def build_index(documents, storage, directory: Path, allowlist: dict[str, str], scopes):
    manifest = {"version": VERSION, "documents": []}
    for doc in documents:
        entry = {
            "document_id": str(doc.id),
            "source_id": str(doc.source_id),
            "checksum_sha256": doc.checksum_sha256,
            "asset_ids": scopes.get(str(doc.source_id), []),
            "admissible": False,
        }
        manifest["documents"].append(entry)
        if allowlist.get(str(doc.id)) != doc.checksum_sha256:
            entry["status"] = "NOT_AUTHORIZED"
            continue
        try:
            data = read_pdf(storage, doc)
            path = directory / f"{doc.id}.json"
            try:
                index = load_index(path, doc)
            except (OSError, ValueError, KeyError, TypeError):
                index = extract(doc, data)
                atomic_json(path, index)
            entry.update(
                page_count=index["page_count"],
                text_pages=sum(p["indexed"] for p in index["coverage"]),
                characters=sum(p["characters"] for p in index["coverage"]),
                chunk_count=len(index["chunks"]),
                admissible=bool(index["chunks"]),
                status="INDEXED" if index["chunks"] else "NO_EXTRACTABLE_TEXT",
            )
        except (OSError, ValueError, KeyError, TypeError, PdfReadError):
            # PDF/parser errors and storage paths must not escape into public reports.
            entry["status"] = "UNAVAILABLE_OR_INVALID_PDF"
    atomic_json(directory / "rag_corpus_manifest.json", manifest)
    return manifest


def inspect_document(storage, settings, doc, allowlist):
    """Read-only diagnostics; authorization precedes every filesystem access."""
    if allowlist.get(str(doc.id)) != doc.checksum_sha256:
        return None, ["NOT_AUTHORIZED"]
    try:
        read_pdf(storage, doc)
    except FileNotFoundError:
        return None, ["DOCUMENT_MISSING"]
    except (OSError, ValueError, KeyError, TypeError):
        return None, ["DOCUMENT_INVALID"]
    try:
        index = load_index(settings.rag_lite_index_dir / f"{doc.id}.json", doc)
        pages = index["coverage"]
        if not pages or any(not isinstance(p["characters"], int) for p in pages):
            raise ValueError("INVALID_COVERAGE")
        if not index["chunks"]:
            return index, [
                "IMAGE_ONLY"
                if all(p["characters"] == 0 for p in pages)
                else "EXTRACTION_LIMITED"
            ]
        return index, ["EXTRACTION_LIMITED"] if any(
            not p["indexed"] for p in pages
        ) else []
    except (OSError, ValueError, KeyError, TypeError):
        return None, ["INDEX_INVALID"]
