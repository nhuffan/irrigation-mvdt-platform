"""Opt-in section boundaries; original normalized page text and offsets are retained."""

import io
import json
import re
from itertools import pairwise
from uuid import UUID

from pypdf import PdfReader

from app.services.rag_lite.indexer import CHUNK_CHARS, MAX_PAGES, VERSION, digest

PROFILE = "section-boundaries-v1"
PARTIAL_PROFILE = "section-pages-v1"


def reviewed_pages(page_count, included_pages=None):
    """Bound extraction, not the immutable original's physical page numbering."""
    if type(page_count) is not int or page_count < 1:
        raise ValueError("SECTION_PAGE_INVALID")
    if included_pages is None:
        if page_count > MAX_PAGES:
            raise ValueError("ENCRYPTED_OR_PAGE_COUNT_LIMIT")
        return list(range(1, page_count + 1))
    if (
        not isinstance(included_pages, list)
        or not included_pages
        or len(included_pages) > MAX_PAGES
        or any(type(n) is not int or not 1 <= n <= page_count for n in included_pages)
        or len(set(included_pages)) != len(included_pages)
    ):
        raise ValueError("INVALID_OR_OVER_BUDGET_INCLUDED_PAGES")
    return sorted(included_pages)


def extraction_digest(coverage, chunks):
    payload = [
        coverage,
        [{k: v for k, v in c.items() if k != "chunk_id"} for c in chunks],
    ]
    return digest(json.dumps(payload, sort_keys=True).encode())


def scope_digest(sections, review, selection=None):
    payload = [PROFILE, sections, review]
    if selection is not None:
        payload = [PARTIAL_PROFILE, sections, review, selection]
    return digest(json.dumps(payload, sort_keys=True).encode())


def chunk_identity(doc_id, checksum, chunk, scope_sha, profile=PROFILE):
    return digest(
        f"{VERSION}:{doc_id}:{checksum}:{chunk['page']}:{chunk['offset']}:"
        f"{chunk['sha256']}:{profile}:{scope_sha}".encode()
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


def extract_sections(doc, data, sections, review, included_pages=None):
    if not review.strip():
        raise ValueError("SECTION_REVIEW_REFERENCE_REQUIRED")
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("ENCRYPTED_OR_PAGE_COUNT_LIMIT")
    selected = reviewed_pages(len(reader.pages), included_pages)
    if included_pages is not None and not sections:
        raise ValueError("PARTIAL_DOCUMENT_REQUIRES_SECTIONS")
    raw = {n: reader.pages[n - 1].extract_text() or "" for n in selected}
    pages = {n: re.sub(r"\s+", " ", text).strip() for n, text in raw.items()}
    compiled = []
    for section in sections:
        page = section["page"]
        if type(page) is not int or page not in pages:
            raise ValueError("SECTION_PAGE_INVALID")
        text = pages[page]
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
    for page, text in pages.items():
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
                "characters": len(raw[page].strip()),
                "indexed": (
                    any(c["page"] == page for c in chunks)
                    if included_pages is not None
                    else len(text) >= 40
                ),
            }
        )
    result = {
        "version": VERSION,
        "document_id": str(doc.id),
        "source_id": str(doc.source_id),
        "checksum_sha256": doc.checksum_sha256,
        "page_count": len(reader.pages),
        "coverage": coverage,
        "chunks": chunks,
        "profile": PROFILE,
        "sections": compiled,
        "scope_review": review,
        "scope_sha256": pin,
    }
    if included_pages is not None:
        integrity = extraction_digest(coverage, chunks)
        selection = {
            "page_count": len(reader.pages),
            "included_pages": selected,
            "extraction_sha256": integrity,
        }
        pin = scope_digest(compiled, review, selection)
        result.update(
            profile=PARTIAL_PROFILE,
            included_pages=selected,
            extraction_sha256=integrity,
            scope_sha256=pin,
        )
        for chunk in chunks:
            chunk["chunk_id"] = chunk_identity(
                doc.id, doc.checksum_sha256, chunk, pin, PARTIAL_PROFILE
            )
    return result


def validate_sections(index, doc):
    profile = index.get("profile")
    if profile not in {PROFILE, PARTIAL_PROFILE}:
        raise ValueError("UNKNOWN_EXTRACTION_PROFILE")
    selection = None
    if profile == PARTIAL_PROFILE:
        pages = reviewed_pages(index["page_count"], index["included_pages"])
        if (
            pages != index["included_pages"]
            or getattr(doc, "page_count", None) != index["page_count"]
            or not index["sections"]
            or any(s["page"] not in pages for s in index["sections"])
            or [p["page"] for p in index["coverage"]] != pages
            or any(c["page"] not in pages for c in index["chunks"])
        ):
            raise ValueError("INVALID_PARTIAL_DOCUMENT_SCOPE")
        for coverage in index["coverage"]:
            if (
                type(coverage["characters"]) is not int
                or coverage["characters"] < 0
                or type(coverage["indexed"]) is not bool
                or coverage["indexed"]
                != any(c["page"] == coverage["page"] for c in index["chunks"])
            ):
                raise ValueError("INVALID_PARTIAL_COVERAGE")
        integrity = extraction_digest(index["coverage"], index["chunks"])
        if integrity != index["extraction_sha256"]:
            raise ValueError("PARTIAL_EXTRACTION_CHANGED")
        selection = {
            "page_count": index["page_count"],
            "included_pages": pages,
            "extraction_sha256": integrity,
        }
    elif "included_pages" in index or "extraction_sha256" in index:
        raise ValueError("MISSING_PARTIAL_DOCUMENT_PROFILE")
    pin = scope_digest(index["sections"], index["scope_review"], selection)
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
        if chunk["chunk_id"] != chunk_identity(
            doc.id, doc.checksum_sha256, chunk, pin, profile
        ):
            raise ValueError("INVALID_SCOPED_CHUNK")


def scoped_chunks(index, asset_id=None):
    return [
        c
        for c in index["chunks"]
        if asset_id is None or "profile" not in index or str(asset_id) in c["asset_ids"]
    ]
