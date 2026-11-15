from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError

from app.services.rag_lite.retriever import EvidenceSelection

MAX_GRANT_BYTES = 64 * 1024
Checksum = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class McpGrant(BaseModel):
    """Operator-provided permission for a specific MCP host and research scope."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[1] = 1
    authorization: str = Field(min_length=1, max_length=512)
    reservoir_id: UUID
    asset_ids: frozenset[UUID] = Field(default_factory=frozenset, max_length=512)
    source_ids: frozenset[UUID] = Field(default_factory=frozenset, max_length=512)
    document_checksums: dict[UUID, Checksum] = Field(
        default_factory=dict, max_length=512
    )
    allow_evidence: StrictBool = False
    allow_links: StrictBool = False

    def selection(self) -> EvidenceSelection:
        return EvidenceSelection(self.source_ids, self.document_checksums)


def load_grant(path: Path | None) -> McpGrant | None:
    if path is None:
        return None
    try:
        with path.open("rb") as stream:
            payload = stream.read(MAX_GRANT_BYTES + 1)
        if len(payload) <= MAX_GRANT_BYTES:
            return McpGrant.model_validate_json(payload)
    except (OSError, ValidationError):
        pass
    return None
