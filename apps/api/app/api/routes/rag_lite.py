"""Separate read-only transaction and bounded local preview endpoints."""

from collections import deque
from threading import Lock
from time import monotonic
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import read_only_session
from app.schemas.rag_lite import RagCoverage, RagQuery, RagResponse
from app.services.rag_lite.generation import generation_available, grounded_response
from app.services.rag_lite.retriever import retrieve
from app.services.storage_service import get_storage
from app.storage.base import Storage

router = APIRouter(prefix="/experimental/rag-lite", tags=["Experimental future work"])
_requests: dict[str, deque] = {}
_lock = Lock()


def enabled():
    if not settings.rag_lite_enabled:
        raise HTTPException(404, "Experimental preview is disabled")


def get_rag_db():
    with read_only_session() as db:
        yield db


def rate_limit(request: Request):
    # Local single-process POC; a public multi-worker deployment needs shared limits/auth.
    key = request.client.host if request.client else "local"
    now = monotonic()
    with _lock:
        for old in [k for k, v in _requests.items() if not v or now - v[-1] >= 60]:
            del _requests[old]
        history = _requests.setdefault(key, deque())
        while history and now - history[0] >= 60:
            history.popleft()
        if len(history) >= 30 or len(_requests) > 1024:
            raise HTTPException(
                429, "Preview request limit reached", headers={"Retry-After": "60"}
            )
        history.append(now)


@router.get("/status")
def preview_status(response: Response, reservoir_id: UUID | None = None):
    response.headers["Cache-Control"] = "no-store"
    available = generation_available(settings, reservoir_id)
    return {
        "enabled": settings.rag_lite_enabled,
        "generation_available": available,
        "mode": "grounded_answer" if available else "retrieval_only",
        "label": "EXPERIMENTAL / FUTURE WORK",
    }


@router.post(
    "/query",
    response_model=RagResponse,
    dependencies=[Depends(enabled), Depends(rate_limit)],
)
def query(
    body: RagQuery,
    response: Response,
    db: Annotated[Session, Depends(get_rag_db)],
    storage: Annotated[Storage, Depends(get_storage)],
):
    response.headers["Cache-Control"] = "no-store"
    if body.mode == "evidence_only" or not settings.rag_generation_enabled:
        return retrieve(db, storage, settings, body)
    evidence_request = body.model_copy(update={"mode": "evidence_only"})
    evidence = retrieve(db, storage, settings, evidence_request)
    # Everything needed for the answer is already materialized. Close the
    # read-only transaction before checking or contacting the model.
    db.close()
    return grounded_response(settings, body, evidence)


@router.get("/demo-questions", dependencies=[Depends(enabled)])
def demo_questions(
    asset_id: UUID,
    reservoir_id: UUID,
    db: Annotated[Session, Depends(get_rag_db)],
    storage: Annotated[Storage, Depends(get_storage)],
):
    from app.models.asset import Asset
    from app.services.rag_lite.suggestions import suggested_questions

    asset = db.get(Asset, asset_id)
    if not asset or asset.reservoir_id != reservoir_id:
        raise HTTPException(404, "Asset not found")
    return suggested_questions(db, storage, settings, asset)


@router.get(
    "/coverage",
    response_model=RagCoverage,
    response_model_exclude_none=True,
    dependencies=[Depends(enabled)],
)
def search_coverage(
    reservoir_id: UUID,
    response: Response,
    db: Annotated[Session, Depends(get_rag_db)],
    storage: Annotated[Storage, Depends(get_storage)],
    asset_id: UUID | None = None,
):
    from app.models.asset import Asset
    from app.services.rag_lite.coverage import search_coverage as live_coverage

    if asset_id:
        asset = db.get(Asset, asset_id)
        if not asset or asset.reservoir_id != reservoir_id:
            raise HTTPException(404, "Asset not found")
    response.headers["Cache-Control"] = "no-store"
    return live_coverage(db, storage, settings, reservoir_id, asset_id)
