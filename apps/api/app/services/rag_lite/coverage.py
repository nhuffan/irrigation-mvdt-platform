"""Live read-only coverage, using the same scope and integrity gates as retrieval."""

from app.schemas.rag_lite import RagCoverage, RagCoverageDiagnostics
from app.services.rag_lite.indexer import inspect_document, load_allowlist
from app.services.rag_lite.retriever import documents_for_reservoir, reviewed_records


def search_coverage(db, storage, settings, reservoir_id, asset_id=None):
    result = RagCoverage()
    records = (
        [
            r
            for r in reviewed_records(db, asset_id)
            if r.source.reservoir_id == reservoir_id
        ]
        if asset_id
        else []
    )
    source_ids = {r.source_id for r in records}
    docs = [
        d
        for d in documents_for_reservoir(db, reservoir_id)
        if not asset_id or d.source_id in source_ids
    ]
    reasons = []
    diag = (
        RagCoverageDiagnostics(
            asset_id=asset_id,
            reviewed_attributes=len(records),
            direct_documents=len(docs),
        )
        if asset_id
        else None
    )
    if diag:
        if not records:
            reasons.append("NO_REVIEWED_ATTRIBUTE")
        if not docs:
            reasons.append("NO_DIRECT_DOCUMENT")
        sources = {r.source_id: r.source for r in records}
        sources.update({d.source_id: d.source for d in docs})
        diag.unknown_metadata_sources = sum(
            not s.source_date
            or not s.authority_level
            or s.authority_level == "UNKNOWN"
            or not s.title
            or not s.source_code
            for s in sources.values()
        )
        if diag.unknown_metadata_sources:
            reasons.append("SOURCE_METADATA_UNKNOWN")
    allowlist = load_allowlist(settings.rag_lite_allowlist_path)
    counters = {
        "NOT_AUTHORIZED": "not_authorized_documents",
        "DOCUMENT_MISSING": "missing_documents",
        "DOCUMENT_INVALID": "invalid_documents",
        "INDEX_INVALID": "invalid_indexes",
        "EXTRACTION_LIMITED": "extraction_limited_documents",
    }
    for doc in docs:
        index, issues = inspect_document(storage, settings, doc, allowlist)
        reasons.extend(issues)
        if diag:
            for code in issues:
                if code in counters:
                    setattr(diag, counters[code], getattr(diag, counters[code]) + 1)
        if "NOT_AUTHORIZED" in issues:
            continue
        result.authorized_documents += 1
        if index and index["chunks"]:
            result.searchable_documents += 1
            result.searchable_pages += len({c["page"] for c in index["chunks"]})
            result.indexed_chunks += len(index["chunks"])
        elif "IMAGE_ONLY" in issues:
            result.image_only_documents += 1
        else:
            result.unavailable_documents += 1
    if diag:
        diag.reason_codes = list(dict.fromkeys(reasons))
        result.diagnostics = diag
    return result
