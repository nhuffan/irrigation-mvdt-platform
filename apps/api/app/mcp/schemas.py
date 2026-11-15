from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StrictBool

from app.schemas.rag_lite import RagCoverage, RagPagination, RagQuery


class Scope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reservoir_id: UUID
    asset_id: UUID | None = None


class AssetScope(Scope):
    asset_id: UUID


class SourceScope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reservoir_id: UUID
    source_id: UUID


class SearchEvidence(RagQuery):
    mode: Literal["evidence_only"] = "evidence_only"
    all_authorized_docs: StrictBool = False


class ToolResult(BaseModel):
    status: Literal["OK", "ERROR", "RETRIEVAL_ONLY", "NOT_ENOUGH_EVIDENCE"]
    scope: dict[str, JsonValue] | None = None
    citations: list[dict[str, JsonValue]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    asset: dict[str, JsonValue] | None = None
    source: dict[str, JsonValue] | None = None
    coverage: RagCoverage | None = None
    pagination: RagPagination | None = None
