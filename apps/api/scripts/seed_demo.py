"""Seed the SYNTHETIC Demo Reservoir into an isolated public-demo deployment.

Writes fictional rows, PDFs, the PDF allowlist, the local index, the reviewed
provenance sidecar and the model-processing grant. Safe to rerun.

Refuses to run unless ``APP_ENV=demo``, the database holds no reservoir other
than the demo one, and storage is not the repository's private ``storage/``.
It never touches research data and is not research evidence.
"""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.config import generation_model, settings
from app.db.session import SessionLocal
from app.demo.corpus import (
    DOCUMENT_FILES,
    LABEL,
    RECORD_SOURCES,
    RESERVOIR_ID,
    demo_provenance,
    insert_demo_rows,
    location_sidecar,
)
from app.models.asset import Asset
from app.models.media import Document
from app.models.reservoir import Reservoir
from app.services.om_service import list_records
from app.services.rag_lite.indexer import atomic_json, build_index
from app.services.rag_lite.retriever import attribute_citation, reviewed_records
from app.services.reviewed_provenance import BINDING_FIELDS
from app.storage.local import LocalStorage

PRIVATE_STORAGE = Path(__file__).resolve().parents[3] / "storage"


def guard() -> None:
    if settings.app_env != "demo":
        raise SystemExit("Refusing: the demo seed runs only with APP_ENV=demo")
    if settings.storage_root.resolve() == PRIVATE_STORAGE.resolve():
        raise SystemExit("Refusing: STORAGE_ROOT must not be the private storage/")
    if not settings.rag_lite_allowlist_path:
        raise SystemExit("Refusing: set RAG_LITE_ALLOWLIST_PATH for the demo")


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    guard()
    storage = LocalStorage(settings.storage_root)
    with SessionLocal.begin() as db:
        others = db.scalars(
            select(Reservoir.id).where(Reservoir.id != RESERVOIR_ID)
        ).all()
        if others:
            raise SystemExit(
                "Refusing: this database holds non-demo reservoirs; "
                "use an isolated demo database"
            )
        created = db.get(Reservoir, RESERVOIR_ID) is None
        # Merge keeps reruns idempotent and upgrades an existing demo database.
        rows = insert_demo_rows(db)
        files = dict(rows.files)
        locations = location_sidecar(rows.assets)
    atomic_json(
        settings.asset_locations_path or settings.storage_root / "asset_locations.json",
        locations,
    )

    with SessionLocal() as db:
        documents = list(
            db.scalars(
                select(Document)
                .where(Document.id.in_([doc_id for doc_id, _, _ in DOCUMENT_FILES]))
                .order_by(Document.id)
            )
        )
        for key, data in files.items():
            storage.store(key, data)

        assets = list(
            db.scalars(select(Asset).where(Asset.reservoir_id == RESERVOIR_ID))
        )
        sidecar = {"version": 1, "records": {}}
        for asset in assets:
            for record in list_records(db, asset.id, "technical"):
                source_code = RECORD_SOURCES.get(record.id)
                if source_code:
                    sidecar["records"][str(record.id)] = {
                        "record": record.model_dump(
                            mode="json", include=set(BINDING_FIELDS)
                        ),
                        "provenance": demo_provenance(source_code).model_dump(
                            mode="json"
                        ),
                    }
        provenance_path = (
            settings.reviewed_provenance_path
            or settings.storage_root / "reviewed_provenance.json"
        )
        atomic_json(provenance_path, sidecar)

        allowlist = {str(doc.id): doc.checksum_sha256 for doc in documents}
        atomic_json(
            settings.rag_lite_allowlist_path,
            {
                "version": 1,
                "authorization": f"{LABEL}; public demo deployment",
                "documents": [
                    {"document_id": key, "checksum_sha256": value}
                    for key, value in allowlist.items()
                ],
            },
        )
        build_index(documents, storage, settings.rag_lite_index_dir, allowlist, {})

        citations = [
            attribute_citation(record)
            for asset in assets
            for record in reviewed_records(db, asset.id)
        ]
        grant_path = settings.rag_generation_authorization_path
        if grant_path and settings.rag_provider in {"ollama", "anthropic"}:
            atomic_json(
                grant_path,
                {
                    "version": 1,
                    "authorization": (
                        f"{LABEL}. Fictional demo corpus written for this project; "
                        "approved for model processing in the public demo only."
                    ),
                    "provider": settings.rag_provider,
                    "model": generation_model(settings),
                    "data_classification": "SYNTHETIC_DEMO",
                    "reservoir_id": str(RESERVOIR_ID),
                    "records": [
                        {"source_id": str(c.source_id), "citation_id": c.citation_id}
                        for c in citations
                    ],
                    "documents": [
                        {
                            "source_id": str(doc.source_id),
                            "document_id": str(doc.id),
                            "checksum_sha256": doc.checksum_sha256,
                        }
                        for doc in documents
                    ],
                },
            )
    json.dump(
        {
            "reservoir_id": str(RESERVOIR_ID),
            "rows_created": created,
            "documents": len(documents),
            "assets": len(assets),
            "model_files": sum(key.endswith(".glb") for key in files),
            "reviewed_records": len(citations),
            "grant": bool(grant_path),
            "label": LABEL,
        },
        sys.stdout,
        indent=2,
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
