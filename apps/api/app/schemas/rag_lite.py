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


TraceStep = Literal[
    "retrieval",
    "authorization",
    "screening",
    "model_output",
    "citations",
    "numbers",
    "units",
    "content_policy",
]
TRACE_STEPS: tuple[TraceStep, ...] = TraceStep.__args__


class TraceCheck(BaseModel):
    name: TraceStep
    status: Literal["passed", "failed", "skipped"]
    detail: str


class AnswerTrace(BaseModel):
    """Content-free account of how a grounded answer was (or was not) produced.

    Holds counts, aliases, check names and timings only: never the prompt,
    evidence text or raw model output.
    """

    attribute_evidence: int = 0
    passage_evidence: int = 0
    provider: str | None = None
    model: str | None = None
    evidence_sent: int = 0
    aliases: list[str] = Field(default_factory=list)
    latency_ms: int | None = None
    checks: list[TraceCheck] = Field(default_factory=list)

    def add(self, name: TraceStep, status, detail: str) -> None:
        self.checks.append(TraceCheck(name=name, status=status, detail=detail))

    def skip_remaining(self, detail: str = "Not reached") -> None:
        done = {check.name for check in self.checks}
        for name in TRACE_STEPS:
            if name not in done:
                self.add(name, "skipped", detail)


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
    trace: AnswerTrace | None = None


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
