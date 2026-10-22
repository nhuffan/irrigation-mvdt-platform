"""Read-only offline build. Explicit checksum-pinned authorization is mandatory."""

import argparse
import json
from time import perf_counter
from uuid import UUID

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.rag_lite.indexer import build_index, load_allowlist
from app.services.rag_lite.retriever import documents_for_reservoir, source_scopes
from app.storage.local import LocalStorage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reservoir-id", type=UUID, required=True)
    args = parser.parse_args()
    start = perf_counter()
    with SessionLocal() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        manifest = build_index(
            documents_for_reservoir(db, args.reservoir_id),
            LocalStorage(settings.storage_root),
            settings.rag_lite_index_dir,
            load_allowlist(settings.rag_lite_allowlist_path),
            source_scopes(db, args.reservoir_id),
        )
    print(
        json.dumps(
            {
                "documents": manifest["documents"],
                "elapsed_seconds": round(perf_counter() - start, 6),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
