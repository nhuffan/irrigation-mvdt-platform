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

    @model_validator(mode="after")
    def explicit_scope(self):
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


class RagResponse(BaseModel):
    status: Literal[
        "ANSWERED", "RETRIEVAL_ONLY", "NOT_ENOUGH_EVIDENCE", "GENERATION_UNAVAILABLE"
    ]
    answer: str | None = None
    asset_id: UUID | None = None
    citations: list[Citation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RagCoverage(BaseModel):
    authorized_documents: int = 0
    searchable_documents: int = 0
    image_only_documents: int = 0
    unavailable_documents: int = 0
    searchable_pages: int = 0
    indexed_chunks: int = 0
