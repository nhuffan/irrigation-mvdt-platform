"""Opt-in section boundaries; original normalized page text and offsets are retained."""

import io
import json
import re
from itertools import pairwise
from uuid import UUID

from pypdf import PdfReader

from app.services.rag_lite.indexer import CHUNK_CHARS, MAX_PAGES, VERSION, digest

PROFILE = "section-boundaries-v1"


def scope_digest(sections, review):
    return digest(json.dumps([PROFILE, sections, review], sort_keys=True).encode())


def chunk_identity(doc_id, checksum, chunk, scope_sha):
    return digest(
        f"{VERSION}:{doc_id}:{checksum}:{chunk['page']}:{chunk['offset']}:"
        f"{chunk['sha256']}:{PROFILE}:{scope_sha}".encode()
    )


def slice_page(doc, page, text, start, end, asset_ids, scope_sha):
    result = []
    while start < end:
        while start < end and text[start].isspace():
            start += 1
        stop = min(start + CHUNK_CHARS, end)
        if stop < end:
            # Prefer a sentence/list boundary; never cut through a number or unit.
            floor = start + CHUNK_CHARS // 2
            boundary = max(text.rfind(". ", floor, stop), text.rfind("; ", floor, stop))
            stop = boundary + 1 if boundary >= floor else text.rfind(" ", floor, stop)
            if stop < floor:
                stop = min(start + CHUNK_CHARS, end)
        excerpt = text[start:stop].rstrip()
        if len(excerpt) >= 40:
            chunk = {
                "page": page,
                "offset": start,
                "text": excerpt,
                "sha256": digest(excerpt.encode()),
                "asset_ids": asset_ids,
            }
            chunk["chunk_id"] = chunk_identity(
                doc.id, doc.checksum_sha256, chunk, scope_sha
            )
            result.append(chunk)
        start = stop
    return result


def extract_sections(doc, data, sections, review):
    if not review.strip():
        raise ValueError("SECTION_REVIEW_REFERENCE_REQUIRED")
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted or not 0 < len(reader.pages) <= MAX_PAGES:
        raise ValueError("ENCRYPTED_OR_PAGE_COUNT_LIMIT")
    raw = [p.extract_text() or "" for p in reader.pages]
    pages = [re.sub(r"\s+", " ", s).strip() for s in raw]
    compiled = []
    for section in sections:
        page = section["page"]
        if not isinstance(page, int) or not 1 <= page <= len(pages):
            raise ValueError("SECTION_PAGE_INVALID")
        text = pages[page - 1]
        marker = re.sub(r"\s+", " ", section["start"]).strip()
        end_marker = re.sub(r"\s+", " ", section.get("end") or "").strip()
        if not marker or text.count(marker) != 1:
            raise ValueError("SECTION_START_NOT_UNIQUE")
        start = text.index(marker)
        if end_marker and text[start + len(marker) :].count(end_marker) != 1:
            raise ValueError("SECTION_END_NOT_UNIQUE")
        end = text.index(end_marker, start + len(marker)) if end_marker else len(text)
        ids = sorted({str(UUID(v)) for v in section["asset_ids"]})
        if not ids or start >= end:
            raise ValueError("SECTION_SCOPE_REQUIRED")
        compiled.append({"page": page, "start": start, "end": end, "asset_ids": ids})
    compiled.sort(key=lambda s: (s["page"], s["start"]))
    for previous, current in pairwise(compiled):
        if previous["page"] == current["page"] and previous["end"] > current["start"]:
            raise ValueError("OVERLAPPING_SECTIONS")
    pin = scope_digest(compiled, review)
    chunks, coverage = [], []
    for page, text in enumerate(pages, 1):
        page_sections = [s for s in compiled if s["page"] == page]
        boundaries = sorted(
            {0, len(text), *[n for s in page_sections for n in (s["start"], s["end"])]}
        )
        if len(text) >= 40:
            for start, end in pairwise(boundaries):
                ids = next(
                    (
                        s["asset_ids"]
                        for s in page_sections
                        if s["start"] <= start and end <= s["end"]
                    ),
                    [],
                )
                chunks.extend(slice_page(doc, page, text, start, end, ids, pin))
        coverage.append(
            {
                "page": page,
                "characters": len(raw[page - 1].strip()),
                "indexed": len(text) >= 40,
            }
        )
    return {
        "version": VERSION,
        "document_id": str(doc.id),
        "source_id": str(doc.source_id),
        "checksum_sha256": doc.checksum_sha256,
        "page_count": len(pages),
        "coverage": coverage,
        "chunks": chunks,
        "profile": PROFILE,
        "sections": compiled,
        "scope_review": review,
        "scope_sha256": pin,
    }


def validate_sections(index, doc):
    if index.get("profile") != PROFILE:
        raise ValueError("UNKNOWN_EXTRACTION_PROFILE")
    pin = scope_digest(index["sections"], index["scope_review"])
    if not index["scope_review"].strip() or pin != index["scope_sha256"]:
        raise ValueError("SECTION_SCOPE_CHANGED")
    for chunk in index["chunks"]:
        start, end = chunk["offset"], chunk["offset"] + len(chunk["text"])
        sections = [s for s in index["sections"] if s["page"] == chunk["page"]]
        ids = next(
            (
                s["asset_ids"]
                for s in sections
                if s["start"] <= start and end <= s["end"]
            ),
            [],
        )
        if chunk["asset_ids"] != ids or any(
            start < s["end"]
            and end > s["start"]
            and not (s["start"] <= start and end <= s["end"])
            for s in sections
        ):
            raise ValueError("CHUNK_CROSSES_ASSET_SECTION")
        if chunk["chunk_id"] != chunk_identity(doc.id, doc.checksum_sha256, chunk, pin):
            raise ValueError("INVALID_SCOPED_CHUNK")


def scoped_chunks(index, asset_id=None):
    return [
        c
        for c in index["chunks"]
        if asset_id is None or "profile" not in index or str(asset_id) in c["asset_ids"]
    ]
