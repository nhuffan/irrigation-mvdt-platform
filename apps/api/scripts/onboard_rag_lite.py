"""Dry-run first, checksum-pinned incremental onboarding into the existing local corpus."""

import argparse
import fcntl
import json
from pathlib import Path

from pypdf.errors import PdfReadError

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.rag_lite.onboarding import apply_prepared, outcome, prepare
from app.storage.local import LocalStorage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Batch {documents:[{file,source_code,document_code,asset_ids,checksum_sha256?,sections?,scope_review?,included_pages?}]}",
    )
    parser.add_argument("--file", type=Path)
    parser.add_argument("--source-code")
    parser.add_argument(
        "--document-code",
        action="append",
        help="Stable code; with --manifest, selects only these entries",
    )
    parser.add_argument("--asset-id", action="append")
    parser.add_argument(
        "--sections",
        type=Path,
        help="Reviewed {sections:[{page,start,end,asset_ids}],scope_review,included_pages?} mapping",
    )
    parser.add_argument(
        "--section",
        action="append",
        help="Reviewed boundary: PAGE|ASSET_UUID|START_TEXT|END_TEXT (empty end means page end)",
    )
    parser.add_argument(
        "--include-page",
        type=int,
        action="append",
        help="Physical original page to extract (repeat); requires reviewed section boundaries",
    )
    parser.add_argument(
        "--scope-review",
        help="Actual section review reference, without promoting verification",
    )
    parser.add_argument(
        "--checksum-sha256",
        help="Expected original checksum; a mismatch fails before changes",
    )
    parser.add_argument(
        "--authorize",
        action="store_true",
        help="Assert an existing explicit local-indexing permission, with its reference",
    )
    parser.add_argument(
        "--authorization-reference",
        help="Actual human permission reference; no external processing permission implied",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Without this flag, no DB/storage/index/authorization writes",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="New machine-readable result file, never overwritten",
    )
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Outcome already exists; preserve previous measurements")
    if args.authorize != bool(args.authorization_reference):
        parser.error(
            "--authorize and --authorization-reference must be supplied together"
        )
    try:
        if args.manifest:
            if any(
                [
                    args.file,
                    args.source_code,
                    args.asset_id,
                    args.sections,
                    args.checksum_sha256,
                    args.section,
                    args.scope_review,
                    args.include_page,
                ]
            ):
                parser.error("Choose a manifest or a single file, not both")
            entries = json.loads(args.manifest.read_text())["documents"]
            if args.document_code:
                selected = set(args.document_code)
                entries = [e for e in entries if e["document_code"] in selected]
                if {e["document_code"] for e in entries} != selected:
                    parser.error("Selected document code is absent from manifest")
        else:
            if (
                not args.file
                or not args.source_code
                or not args.document_code
                or len(args.document_code) != 1
                or not args.asset_id
            ):
                parser.error(
                    "Single file requires --file, --source-code, one --document-code and --asset-id"
                )
            entries = [
                {
                    "file": str(args.file),
                    "source_code": args.source_code,
                    "document_code": args.document_code[0],
                    "asset_ids": args.asset_id,
                    "checksum_sha256": args.checksum_sha256,
                }
            ]
            if args.sections and args.section:
                parser.error("Choose --sections or repeated --section flags")
            if args.sections:
                section_review = json.loads(args.sections.read_text())
                if not isinstance(section_review, dict) or set(section_review) - {
                    "sections",
                    "scope_review",
                    "included_pages",
                }:
                    raise ValueError("SECTION_FILE_CANNOT_OVERRIDE_DOCUMENT_IDENTITY")
                entries[0].update(section_review)
            if args.include_page:
                if args.sections and "included_pages" in entries[0]:
                    parser.error(
                        "Choose included_pages in --sections or --include-page flags"
                    )
                entries[0]["included_pages"] = args.include_page
            if args.section:
                if not args.scope_review:
                    parser.error("Section boundaries require --scope-review")
                sections = []
                for raw in args.section:
                    parts = raw.split("|", 3)
                    if len(parts) != 4 or not parts[0].isdigit():
                        parser.error(
                            "--section requires PAGE|ASSET_UUID|START_TEXT|END_TEXT"
                        )
                    sections.append(
                        {
                            "page": int(parts[0]),
                            "asset_ids": [parts[1]],
                            "start": parts[2],
                            "end": parts[3] or None,
                        }
                    )
                entries[0].update(sections=sections, scope_review=args.scope_review)
        # Serialize writers. Dry-run creates no lock, directory or cache.
        lock = None
        if args.apply:
            settings.rag_lite_index_dir.mkdir(parents=True, exist_ok=True)
            lock = (settings.rag_lite_index_dir / ".onboarding.lock").open("a")
            fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with SessionLocal() as db:
                storage = LocalStorage(settings.storage_root)
                prepared = prepare(
                    db, storage, settings, entries, args.authorization_reference
                )
                if args.apply:
                    apply_prepared(
                        db, storage, settings, prepared, args.authorization_reference
                    )
                result = outcome(prepared, args.apply)
        finally:
            if lock:
                lock.close()
    except (ValueError, OSError, KeyError, TypeError, PdfReadError) as error:
        result = {
            "applied": False,
            "documents": [],
            "blockers": [str(error)],
            "status": "FAILED_CLOSED",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.output:
            with args.output.open("x") as output:
                json.dump(result, output, ensure_ascii=False, indent=2)
        return 1
    if args.output:
        with args.output.open("x") as output:
            json.dump(result, output, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
