from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RagQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=2, max_length=1000)
    reservoir_id: UUID
    asset_id: UUID | None = None
    all_authorized_docs: bool = False
    mode: Literal["evidence_only", "grounded_answer"] = "evidence_only"
    query_type: Literal["auto", "attribute", "document"] = "auto"
    attribute_key: str | None = Field(default=None, min_length=1, max_length=100)
    top_k: int = Field(default=5, ge=1, le=8)
    page: int | None = Field(default=None, ge=1, le=10000)
    page_size: int | None = Field(default=None, ge=1, le=20)

    @model_validator(mode="after")
    def explicit_scope(self):
        if (self.page is None) != (self.page_size is None):
            raise ValueError("Pagination requires both page and page_size")
        if self.page is not None and self.mode != "evidence_only":
            raise ValueError("Pagination is for retrieval evidence only")
        if (self.asset_id is None) == (not self.all_authorized_docs):
            raise ValueError(
                "Choose one asset UUID or explicitly search all authorized documents"
            )
        if self.all_authorized_docs and (
            self.attribute_key or self.query_type == "attribute"
        ):
            raise ValueError("Exact attributes require one asset UUID")
        return self


class Citation(BaseModel):
    citation_id: str
    kind: Literal["technical_attribute", "document_chunk"]
    source_id: UUID
    source_code: str
    document_id: UUID | None = None
    record_id: UUID | None = None
    page: int | None = None
    locator: str
    asset_id: UUID | None = None
    url: str
    content_url: str | None = None
    title: str
    excerpt: str
    checksum_sha256: str | None = None
    attribute_key: str | None = None
    value_number: float | None = None
    value_text: str | None = None
    unit: str | None = None
    evidence_id: str | None = None
    source_date: str | None = None
    record_status: str | None = None
    source_status: str
    authority: str | None = None


EvidenceReason = Literal[
    "NO_DIRECT_DOCUMENT",
    "NO_SCOPED_PASSAGE",
    "NO_REVIEWED_ATTRIBUTE",
    "NOT_AUTHORIZED",
    "IMAGE_ONLY",
    "INDEX_INVALID",
    "DOCUMENT_MISSING",
    "DOCUMENT_INVALID",
    "EXTRACTION_LIMITED",
    "NO_MATCH",
    "SOURCE_METADATA_UNKNOWN",
    "OUT_OF_SCOPE",
    "SCOPE_MISMATCH",
]


class RagPagination(BaseModel):
    page: int
    page_size: int
    total_results: int
    total_pages: int


class RagResponse(BaseModel):
    status: Literal[
        "ANSWERED", "RETRIEVAL_ONLY", "NOT_ENOUGH_EVIDENCE", "GENERATION_UNAVAILABLE"
    ]
    answer: str | None = None
    asset_id: UUID | None = None
    citations: list[Citation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reason_codes: list[EvidenceReason] = Field(default_factory=list)
    pagination: RagPagination | None = None


class RagCoverageDiagnostics(BaseModel):
    asset_id: UUID
    reviewed_attributes: int = 0
    direct_documents: int = 0
    unscoped_documents: int = 0
    not_authorized_documents: int = 0
    missing_documents: int = 0
    invalid_documents: int = 0
    invalid_indexes: int = 0
    extraction_limited_documents: int = 0
    unknown_metadata_sources: int = 0
    reason_codes: list[EvidenceReason] = Field(default_factory=list)


class RagCoverage(BaseModel):
    authorized_documents: int = 0
    searchable_documents: int = 0
    image_only_documents: int = 0
    unavailable_documents: int = 0
    searchable_pages: int = 0
    indexed_chunks: int = 0
    diagnostics: RagCoverageDiagnostics | None = None
