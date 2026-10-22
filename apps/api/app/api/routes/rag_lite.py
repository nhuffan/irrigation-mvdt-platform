"""Separate read-only transaction and bounded local preview endpoints."""

from collections import deque
from threading import Lock
from time import monotonic
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.rag_lite import RagQuery, RagResponse
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
    with SessionLocal() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        db.execute(text("SET LOCAL statement_timeout = '5000ms'"))
        yield db
        # Context closes with rollback, never commit.


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
def preview_status(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {
        "enabled": settings.rag_lite_enabled,
        "generation_available": False,
        "mode": "retrieval_only",
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
    return retrieve(db, storage, settings, body)


@router.get("/demo-questions", dependencies=[Depends(enabled)])
def demo_questions(
    asset_id: UUID, reservoir_id: UUID, db: Annotated[Session, Depends(get_rag_db)]
):
    from app.models.asset import Asset
    from app.services.rag_lite.retriever import reviewed_records

    asset = db.get(Asset, asset_id)
    if not asset or asset.reservoir_id != reservoir_id:
        raise HTTPException(404, "Asset not found")
    return [
        {"question": r.attribute_key, "attribute_key": r.attribute_key}
        for r in reviewed_records(db, asset_id)[:4]
    ]
