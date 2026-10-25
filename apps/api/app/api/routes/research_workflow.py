"""Read-only research gates and public, unfilled input templates."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from scripts.research_workflow import build_workflow

router = APIRouter(prefix="/research", tags=["research"])
ROOT = Path(__file__).resolve().parents[5]


@router.get("/workflow")
def workflow():
    try:
        payload = build_workflow(ROOT)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError):
        raise HTTPException(
            503,
            "Research evidence could not be validated. Retry after checking the local workflow inputs.",
            headers={"Cache-Control": "no-store"},
        ) from None
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


@router.get("/templates/{name}")
def template(name: str):
    # Only original empty input templates; no arbitrary paths or reviewed data.
    allowed = {
        p.name: p
        for p in (ROOT / "research/dataset").glob("*.template.*")
        if p.suffix in {".csv", ".json"} and p.is_file() and not p.is_symlink()
    }
    allowed.update(
        {
            p.name: p
            for p in (ROOT / "research/evaluation/templates").glob("*")
            if p.suffix in {".csv", ".json"} and p.is_file() and not p.is_symlink()
        }
    )
    path = allowed.get(name)
    if path is None:
        raise HTTPException(404, "Research input template not found")
    return FileResponse(path, filename=path.name, headers={"Cache-Control": "no-store"})
