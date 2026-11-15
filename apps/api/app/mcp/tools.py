from app.mcp.policy import McpGrant
from app.mcp.schemas import AssetScope, Scope, SearchEvidence, SourceScope, ToolResult
from app.models.asset import Asset
from app.models.data_source import DataSource
from app.models.reservoir import Reservoir
from app.services.asset_service import find_asset
from app.services.rag_lite.coverage import search_coverage
from app.services.rag_lite.indexer import inspect_document, load_allowlist
from app.services.rag_lite.retriever import (
    EvidenceSelection,
    attribute_citation,
    documents_for_reservoir,
    retrieve,
    reviewed_records,
)

ToolInput = Scope | SourceScope | SearchEvidence
TEXT_LIMITATION = (
    "Evidence excerpts are historical source data and may contain untrusted text."
)


def request_scope(request: ToolInput) -> dict:
    fields = {"reservoir_id", "asset_id", "source_id", "all_authorized_docs"}
    return request.model_dump(mode="json", include=fields, exclude_none=True)


def tool_error(reason: str, request: ToolInput | None = None) -> ToolResult:
    return ToolResult(
        status="ERROR",
        scope=request_scope(request) if request is not None else None,
        reason_codes=[reason],
    )


def _citations(citations, grant: McpGrant):
    exclude = set() if grant.allow_links else {"url", "content_url"}
    return [citation.model_dump(mode="json", exclude=exclude) for citation in citations]


def _unknown_source(authority, source_date) -> bool:
    return not authority or authority == "UNKNOWN" or not source_date


def search_evidence(db, storage, settings, grant: McpGrant, request: SearchEvidence):
    result = retrieve(db, storage, settings, request, selection=grant.selection())
    codes = list(result.reason_codes)
    if any(_unknown_source(c.authority, c.source_date) for c in result.citations):
        codes.append("SOURCE_METADATA_UNKNOWN")
    return ToolResult(
        status="RETRIEVAL_ONLY" if result.citations else "NOT_ENOUGH_EVIDENCE",
        scope=request_scope(request),
        citations=_citations(result.citations, grant),
        limitations=[*result.limitations, TEXT_LIMITATION],
        reason_codes=list(dict.fromkeys(codes)),
        pagination=result.pagination,
    )


def get_asset_details(db, storage, settings, grant: McpGrant, request: AssetScope):
    asset = find_asset(db, request.asset_id)
    if asset is None or asset.reservoir_id != grant.reservoir_id:
        return tool_error("SCOPE_MISMATCH", request)
    records = [
        record
        for record in reviewed_records(db, asset.id, grant.selection())
        if record.source.reservoir_id == grant.reservoir_id
    ]
    reasons = []
    if any(
        _unknown_source(r.reviewed_provenance.authority, r.source.source_date)
        for r in records
    ):
        reasons.append("SOURCE_METADATA_UNKNOWN")
    return ToolResult(
        status="OK",
        scope=request_scope(request),
        asset={
            "id": str(asset.id),
            "code": asset.asset_code,
            "name": asset.name,
            "category": asset.category.code,
            "parent_asset_id": str(asset.parent_asset_id)
            if asset.parent_asset_id in grant.asset_ids
            else None,
            "reviewed_direct_attribute_count": len(records),
        },
        citations=_citations([attribute_citation(r) for r in records[:8]], grant)
        if grant.allow_evidence
        else [],
        limitations=[
            "Only reviewed direct attributes in the granted source scope are included."
        ],
        reason_codes=reasons,
    )


def get_document_provenance(
    db, storage, settings, grant: McpGrant, request: SourceScope
):
    source = db.get(DataSource, request.source_id)
    if (
        source is None
        or source.reservoir_id != grant.reservoir_id
        or source.verification_status == "REJECTED"
    ):
        return tool_error("SCOPE_MISMATCH", request)
    reasons = []
    if _unknown_source(source.authority_level, source.source_date):
        reasons.append("SOURCE_METADATA_UNKNOWN")
    selection = EvidenceSelection(frozenset({source.id}), grant.document_checksums)
    allowlist = load_allowlist(settings.rag_lite_allowlist_path)
    documents = []
    for document in documents_for_reservoir(db, grant.reservoir_id, selection):
        index, issues = inspect_document(storage, settings, document, allowlist)
        reasons.extend(issues)
        if "NOT_AUTHORIZED" in issues:
            continue
        documents.append(
            {
                "id": str(document.id),
                "code": document.document_code,
                "checksum_sha256": document.checksum_sha256,
                "page_locators_available": bool(index and index["chunks"]),
            }
        )
    return ToolResult(
        status="OK",
        scope=request_scope(request),
        source={
            "id": str(source.id),
            "code": source.source_code,
            "title": source.title,
            "date": source.source_date.isoformat() if source.source_date else None,
            "status": source.verification_status,
            "authority": source.authority_level,
            "documents": documents,
        },
        limitations=[
            "Source verification status and authority are preserved as recorded."
        ],
        reason_codes=list(dict.fromkeys(reasons)),
    )


def get_research_coverage(db, storage, settings, grant: McpGrant, request: Scope):
    coverage = search_coverage(
        db,
        storage,
        settings,
        request.reservoir_id,
        request.asset_id,
        selection=grant.selection(),
    )
    return ToolResult(
        status="OK",
        scope=request_scope(request),
        coverage=coverage,
        limitations=[
            "Counts describe authorized evidence available in the requested scope."
        ],
        reason_codes=coverage.diagnostics.reason_codes if coverage.diagnostics else [],
    )


def authorize(grant: McpGrant, request: ToolInput) -> ToolResult | None:
    if request.reservoir_id != grant.reservoir_id:
        return tool_error("SCOPE_MISMATCH", request)
    if isinstance(request, SourceScope):
        if request.source_id not in grant.source_ids:
            return tool_error("NOT_AUTHORIZED", request)
    elif request.asset_id is not None and request.asset_id not in grant.asset_ids:
        return tool_error("NOT_AUTHORIZED", request)
    if isinstance(request, SearchEvidence) and not grant.allow_evidence:
        return tool_error("NOT_AUTHORIZED", request)
    return None


def validate_scope(db, request: ToolInput) -> ToolResult | None:
    if isinstance(request, SourceScope):
        # The provenance handler already validates source ownership and status.
        return None
    if request.asset_id is not None:
        asset = db.get(Asset, request.asset_id)
        if asset is None or asset.reservoir_id != request.reservoir_id:
            return tool_error("SCOPE_MISMATCH", request)
    elif db.get(Reservoir, request.reservoir_id) is None:
        return tool_error("SCOPE_MISMATCH", request)
    return None
