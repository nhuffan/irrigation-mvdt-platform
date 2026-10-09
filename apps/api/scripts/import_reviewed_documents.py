"""B03 retained-byte review gate; isolated-storage dry-run by default."""

import argparse
import hashlib
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, uuid5

from pypdf import PdfReader
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import asset, asset_category, reservoir  # noqa: F401
from app.models.data_source import DataSource
from app.models.media import Document
from app.services.document_service import import_document
from app.services.storage_service import get_storage
from app.storage.local import LocalStorage
from scripts.prepare_reviewed_om_batch import read_rows
from scripts.research_common import digest, write_csv

STATUSES = {
    "IMPORT",
    "DUPLICATE_REPRESENTATION",
    "REFERENCE_ONLY",
    "MISSING",
    "REJECTED",
}


def validate_manifest(rows, evidence, root):
    evidence_map = {e["evidence_id"]: e for e in evidence}
    if len(evidence_map) != len(evidence):
        raise ValueError("Duplicate evidence IDs")
    selected, codes, physical_sources = [], set(), {}
    for row in rows:
        code = row["document_code"]
        if not code.startswith("RS-DOC-") or code in codes:
            raise ValueError("Unique stable RS document code required")
        codes.add(code)
        if row["document_status"] not in STATUSES:
            raise ValueError("Unknown document decision")
        if row["document_status"] != "IMPORT":
            continue
        if (
            not row["reviewer"].strip()
            or datetime.fromisoformat(row["reviewed_at"]).utcoffset() is None
        ):
            raise ValueError("Reviewer and timezone-aware timestamp required")
        e = evidence_map[row["evidence_id"]]
        if (
            not row["source_code"].startswith("RS-")
            or any(
                row[k] != e[k]
                for k in ("source_code", "drive_file_id", "file_name", "mime_type")
            )
            or e["review_status"] not in {"REVIEWED", "VERIFIED"}
        ):
            raise ValueError("Reviewed physical evidence linkage mismatch")
        if (
            "folder" in row["mime_type"]
            or not row["representation_group"].strip()
            or not row["drive_file_id"].strip()
        ):
            raise ValueError("Physical file and representation decision required")
        path = (root / row["file_path"]).resolve()
        if (
            not path.is_relative_to(root.resolve())
            or not path.is_file()
            or path.name != row["file_name"]
        ):
            raise ValueError(
                "Retained file must exist under evidence root with original filename"
            )
        data = path.read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        if checksum != row["checksum_sha256"] or len(data) != int(row["file_size"]):
            raise ValueError("Retained bytes differ from reviewed manifest")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if mime != row["mime_type"]:
            raise ValueError("MIME/extension mismatch")
        pages = len(PdfReader(path).pages) if mime == "application/pdf" else None
        if pages != (int(row["page_count"]) if row["page_count"] else None):
            raise ValueError("Actual PDF page count differs from review")
        for identity in ("hash:" + checksum, "drive:" + row["drive_file_id"]):
            if identity in physical_sources:
                raise ValueError(
                    "Duplicate physical file; review representation/source modeling"
                )
            physical_sources[identity] = row["source_code"]
        selected.append((row, path, pages))
    if not selected:
        raise ValueError("No reviewed IMPORT documents")
    return selected


def import_reviewed(db, storage, selected):
    results = []
    for row, path, pages in selected:
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["checksum_sha256"]:
            raise ValueError("Retained bytes changed after review validation")
        source = db.scalar(
            select(DataSource).where(DataSource.source_code == row["source_code"])
        )
        if (
            source is None
            or source.verification_status == "REJECTED"
            or not source.source_code.startswith("RS-")
        ):
            raise ValueError("Existing non-rejected RS source required")
        stable_id = uuid5(NAMESPACE_URL, f"B03:{source.id}:{row['document_code']}")
        by_code = db.scalar(
            select(Document).where(Document.document_code == row["document_code"])
        )
        by_hash = db.scalar(
            select(Document).where(
                Document.source_id == source.id,
                Document.checksum_sha256 == row["checksum_sha256"],
            )
        )
        if by_code is not by_hash or (by_hash is not None and by_hash.id != stable_id):
            raise ValueError(
                "Existing identity differs; do not overwrite or silently alias codes"
            )
        if by_hash:
            expected = {
                "original_file_name": row["file_name"],
                "mime_type": row["mime_type"],
                "file_size": int(row["file_size"]),
                "page_count": pages,
            }
            if any(getattr(by_hash, k) != v for k, v in expected.items()):
                raise ValueError(
                    "Existing metadata differs; reviewed correction required"
                )
        document = import_document(
            db, storage, row["source_code"], path, row["document_code"]
        )
        if by_hash is None:
            document.id = stable_id
            document.page_count = pages
            db.flush()
        if (
            hashlib.sha256(storage.path(document.storage_key).read_bytes()).hexdigest()
            != row["checksum_sha256"]
        ):
            raise ValueError("Stored bytes checksum mismatch")
        results.append(
            {
                "document_id": str(document.id),
                "document_code": row["document_code"],
                "source_code": row["source_code"],
                "evidence_id": row["evidence_id"],
                "checksum_sha256": row["checksum_sha256"],
                "page_count": pages,
                "status": "UNCHANGED" if by_hash else "STAGED",
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser()
    for key in ("manifest", "evidence", "evidence-root", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve existing audit output")
    rows, evidence = read_rows(args.manifest), read_rows(args.evidence)
    selected = validate_manifest(rows, evidence, args.evidence_root)
    hashes = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [args.manifest, args.evidence]
    }
    with TemporaryDirectory(prefix="b03-doc-dry-run-") as temp, SessionLocal() as db:
        storage = get_storage() if args.apply else LocalStorage(Path(temp))
        try:
            results = import_reviewed(db, storage, selected)
            for row in results:
                if row["status"] == "STAGED":
                    row["status"] = "IMPORTED" if args.apply else "DRY_RUN"
            args.output.mkdir(parents=True)
            write_csv(args.output / "log.csv", results, list(results[0]))
            report = {
                "manifest_sha256": digest(rows),
                "input_sha256": hashes,
                "applied": args.apply,
                "records": results,
                "storage_note": "Content-addressed files retained on apply; DB transaction atomic. Dry-run uses temporary storage.",
            }
            (args.output / "verification_report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            )
            if args.apply:
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
            if args.output.exists():
                (args.output / "FAILED").write_text(
                    "Run failed; do not use success intent logs as proof of commit.\n"
                )
            raise
    print(
        json.dumps(
            {
                "count": len(results),
                "applied": args.apply,
                "statuses": [r["status"] for r in results],
            }
        )
    )


if __name__ == "__main__":
    main()
