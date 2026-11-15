"""Local model authorization and process-local generation budgets."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.schemas.rag_lite import Citation, RagQuery, RagResponse
from app.services.rag_lite.answer import generate_answer, generation_unavailable
from app.services.rag_lite.providers import provider_for

logger = logging.getLogger(__name__)
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
RecordCitationId = Annotated[str, Field(pattern=r"^attr-[0-9a-f-]{36}-[0-9a-f]{16}$")]


class AuthorizedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_id: UUID
    document_id: UUID
    checksum_sha256: Digest


class AuthorizedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source_id: UUID
    citation_id: RecordCitationId


class GenerationAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    version: Literal[1]
    authorization: str = Field(min_length=1, max_length=1000)
    provider: Literal["ollama"]
    model: str = Field(min_length=1, max_length=137)
    reservoir_id: UUID
    documents: list[AuthorizedDocument] = Field(default_factory=list, max_length=256)
    records: list[AuthorizedRecord] = Field(default_factory=list, max_length=256)

    def eligible(self, citations: list[Citation]) -> list[Citation]:
        documents = {
            (doc.source_id, doc.document_id, doc.checksum_sha256)
            for doc in self.documents
        }
        records = {(row.source_id, row.citation_id) for row in self.records}
        return [
            item
            for item in citations
            if (
                item.kind == "document_chunk"
                and (item.source_id, item.document_id, item.checksum_sha256)
                in documents
            )
            or (
                item.kind == "technical_attribute"
                and (item.source_id, item.citation_id) in records
            )
        ]


def read_authorization(path: Path | None) -> GenerationAuthorization | None:
    if not path or not path.is_file():
        return None
    try:
        with path.open("rb") as source:
            content = source.read(128 * 1024 + 1)
        if len(content) <= 128 * 1024:
            grant = GenerationAuthorization.model_validate_json(content)
            if grant.documents or grant.records:
                return grant
    except (OSError, ValueError):
        pass
    return None


def authorized_provider(settings: Settings, reservoir_id: UUID | None):
    if not settings.rag_lite_enabled or not settings.rag_generation_enabled:
        return None
    provider = provider_for(settings.rag_provider, settings.rag_ollama_model)
    if provider is None:
        return None
    grant = read_authorization(settings.rag_generation_authorization_path)
    if (
        grant is None
        or grant.provider != settings.rag_provider
        or grant.model != settings.rag_ollama_model
        or (reservoir_id is not None and grant.reservoir_id != reservoir_id)
    ):
        return None
    return provider, grant


class GenerationBudget:
    def __init__(self):
        self.lock = Lock()
        self.day = None
        self.attempts = 0
        self.in_progress = 0

    def acquire(self, daily_limit: int, concurrency: int) -> bool:
        with self.lock:
            day = datetime.now(UTC).date()
            if self.day != day:
                self.day = day
                self.attempts = 0
            if self.attempts >= daily_limit or self.in_progress >= concurrency:
                return False
            self.attempts += 1
            self.in_progress += 1
            return True

    def release(self) -> None:
        with self.lock:
            self.in_progress -= 1


budget = GenerationBudget()


def generation_available(settings: Settings, reservoir_id: UUID | None) -> bool:
    configured = authorized_provider(settings, reservoir_id)
    return configured is not None and configured[0].ready()


def grounded_response(
    settings: Settings, request: RagQuery, result: RagResponse
) -> RagResponse:
    if request.mode == "evidence_only" or not result.citations:
        return result
    configured = authorized_provider(settings, request.reservoir_id)
    if configured is None:
        return generation_unavailable(result)
    provider, grant = configured
    evidence = grant.eligible(result.citations)
    if (
        not evidence
        or not provider.ready()
        or not budget.acquire(settings.rag_generation_daily_limit, 1)
    ):
        return generation_unavailable(result)

    request_id = uuid4()
    started = monotonic()
    try:
        return generate_answer(
            request,
            result,
            evidence,
            provider,
            max_context_chars=min(settings.rag_lite_max_context_chars, 12000),
            timeout=settings.rag_generation_timeout_seconds,
        )
    finally:
        budget.release()
        logger.info(
            "RAG generation id=%s model=%s reservoir=%s sources=%s status=%s elapsed_ms=%d",
            request_id,
            settings.rag_ollama_model,
            request.reservoir_id,
            sorted({str(item.source_id) for item in evidence}),
            result.status,
            1000 * (monotonic() - started),
        )
