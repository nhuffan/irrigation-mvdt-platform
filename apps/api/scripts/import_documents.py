"""Import a local file into configured storage; no public upload endpoint."""

import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.models import asset, asset_category, reservoir  # noqa: F401
from app.services.document_service import import_document
from app.services.storage_service import get_storage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-code", required=True)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--document-code", required=True)
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        document = import_document(
            db, get_storage(), args.source_code, args.file, args.document_code
        )
        print(
            f"Document {document.id}: {document.document_code} (SHA-256 {document.checksum_sha256})"
        )


if __name__ == "__main__":
    main()
