"""Capture private read-only DB/media/API evidence for the methodology dashboard.

Run from the repository root with `uv run --project apps/api python ... before`
(or `after`); output remains in the ignored research evidence directory.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "apps/api"))
from app.db.session import SessionLocal
from app.main import app
from app.models.media import Document
from app.models.reservoir import Reservoir
from app.services.storage_service import get_storage
from fastapi.testclient import TestClient
from scripts.import_research_data import TABLES
from scripts.research_common import digest
from sqlalchemy import select, text

out = root / "research/evaluation/evidence/METHODOLOGY-MAP"
out.mkdir(parents=True, exist_ok=True)
with SessionLocal() as db:
    db.execute(text("SET TRANSACTION READ ONLY"))
    rows = {
        k: sorted(
            [
                json.loads(json.dumps(dict(r), default=str))
                for r in db.execute(select(m.__table__)).mappings()
            ],
            key=lambda x: x["id"],
        )
        for k, m in {**TABLES, "documents": Document, "reservoirs": Reservoir}.items()
    }
    storage = {
        r["storage_key"]: hashlib.sha256(
            get_storage().path(r["storage_key"]).read_bytes()
        ).hexdigest()
        for k in ["documents", "models"]
        for r in rows[k]
    }
snapshot = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "rows": rows,
    "storage_sha256": storage,
    "database_fingerprint": digest(rows),
}
phase = sys.argv[1] if len(sys.argv) > 1 else "before"
if phase not in ("before", "after"):
    raise SystemExit("phase must be before or after")
(out / f"db-{phase}.json").write_text(
    json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
)
if phase == "before":
    with TestClient(app) as c:

        def get(p):
            r = c.get("/api/v1/" + p)
            r.raise_for_status()
            return r.json()

        api = {}
        for a in rows["assets"]:
            if a["asset_code"].startswith("RS-"):
                p = "assets/" + a["id"]
                api[a["asset_code"]] = {
                    "asset": get(p),
                    **{
                        k: get(p + "/" + k)
                        for k in [
                            "technical",
                            "documents",
                            "current-condition",
                            "timeline",
                            "model-links",
                        ]
                    },
                }
        (out / "api-readback.json").write_text(
            json.dumps(api, ensure_ascii=False, indent=2) + "\n"
        )
print(phase, snapshot["database_fingerprint"])
print(
    "research assets",
    len([a for a in rows["assets"] if a["asset_code"].startswith("RS-")]),
)
