"""Reference-location operator: dry-run first, stage unapproved candidates, selectively apply.

No database writes. Accepted records are append-only and never become canonical geometry.
"""

import argparse
import fcntl
import hashlib
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from pypdf import PdfReader
from pypdf.errors import PyPdfError
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.data_source import DataSource
from app.models.media import Document
from app.models.reservoir import Reservoir
from app.services.asset_location import LocationReview
from app.services.coordinate_input import (
    CoordinateInput,
    distance_metres,
    parse_coordinates,
)
from app.services.om_service import list_records
from app.services.spatial_candidates import (
    HumanReview,
    SpatialCandidate,
    SpatialDisposition,
)
from app.storage.local import LocalStorage
from scripts.research_common import digest


def default_path():
    return (
        settings.asset_locations_path or settings.storage_root / "asset_locations.json"
    )


def read_bundle(path):
    if not Path(path).exists():
        return {"version": 1, "records": {}}
    value = json.loads(Path(path).read_text())
    if value.get("version") != 1 or not isinstance(value.get("records"), dict):
        raise ValueError("Invalid existing version1 reference sidecar")
    if not isinstance(value.get("candidates", []), list) or not isinstance(
        value.get("dispositions", {}), dict
    ):
        raise TypeError("Invalid candidate/disposition collections")
    # Validate existing records before any write; do not 'repair' them by dropping fields.
    for asset_id, entry in value["records"].items():
        if str(LocationReview.model_validate(entry).asset_id) != asset_id:
            raise ValueError("Existing reference key/identity mismatch")
    candidates = [
        SpatialCandidate.model_validate(item) for item in value.get("candidates", [])
    ]
    if len(candidates) != len({item.candidate_id for item in candidates}):
        raise ValueError("Duplicate existing candidate IDs")
    by_id = {item.candidate_id: item for item in candidates}
    for key, entry in value.get("dispositions", {}).items():
        disposition = SpatialDisposition.model_validate(entry)
        if str(disposition.asset_id) != key or any(
            candidate_id not in by_id
            or by_id[candidate_id].asset_id != disposition.asset_id
            for candidate_id in disposition.candidate_ids
        ):
            raise ValueError("Invalid existing disposition candidate binding")
    return value


def candidate_digest(value):
    return digest(value.model_dump(mode="json", exclude={"review"}))


def load_packet(path):
    packet = json.loads(Path(path).read_text())
    if packet.get("version") != 1 or set(packet) - {
        "version",
        "candidates",
        "dispositions",
    }:
        raise ValueError("Candidate packet must use version1 and known fields")
    candidates = [
        SpatialCandidate.model_validate(value) for value in packet.get("candidates", [])
    ]
    if len({value.candidate_id for value in candidates}) != len(candidates):
        raise ValueError("Duplicate candidate ID")
    dispositions = {
        key: SpatialDisposition.model_validate(value)
        for key, value in packet.get("dispositions", {}).items()
    }
    for key, value in dispositions.items():
        if str(value.asset_id) != key:
            raise ValueError("Disposition key/UUID mismatch")
    return candidates, dispositions


def identity(db, value):
    asset = db.get(Asset, value.asset_id)
    if not asset or (asset.reservoir_id, asset.asset_code) != (
        value.reservoir_id,
        value.asset_code,
    ):
        raise ValueError("ASSET_IDENTITY_MISMATCH")
    if (
        isinstance(value, SpatialCandidate)
        and asset.parent_asset_id != value.parent_asset_id
    ):
        raise ValueError("ASSET_HIERARCHY_MISMATCH")
    if not asset.asset_code.startswith("RS-"):
        raise ValueError("RESEARCH_ASSET_REQUIRED")
    return asset


def source_check(db, value, *, require_asset_binding=False):
    path = Path(value.original_path).resolve(strict=True)
    if (
        not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != value.source_sha256
    ):
        raise ValueError("ORIGINAL_CHECKSUM_MISMATCH")
    try:
        original = PdfReader(path)
        page_count = len(original.pages)
    except (PyPdfError, OSError, ValueError, TypeError) as exc:
        raise ValueError("SOURCE_ORIGINAL_UNREADABLE") from exc
    if value.physical_page > page_count:
        raise ValueError("PHYSICAL_PAGE_OUT_OF_RANGE")
    if value.source_id:
        source = db.get(DataSource, value.source_id)
        if (
            not source
            or source.reservoir_id != value.reservoir_id
            or not source.source_code.startswith("RS-")
        ):
            raise ValueError("SOURCE_IDENTITY_MISMATCH")
        if require_asset_binding and source.verification_status == "REJECTED":
            raise ValueError("SOURCE_REJECTED")
    if value.document_id:
        document = db.get(Document, value.document_id)
        if not document or not value.source_id or document.source_id != value.source_id:
            raise ValueError("DOCUMENT_SOURCE_MISMATCH")
        registered_path = LocalStorage(settings.storage_root).path(document.storage_key)
        if (
            document.checksum_sha256 != value.source_sha256
            or registered_path.read_bytes() != path.read_bytes()
        ):
            raise ValueError("REGISTERED_DOCUMENT_CHECKSUM_MISMATCH")
        if document.page_count is not None and document.page_count != len(
            original.pages
        ):
            raise ValueError("REGISTERED_DOCUMENT_PAGE_COUNT_MISMATCH")
    if require_asset_binding and value.source_id:
        existing_binding = any(
            record.source_id == value.source_id
            and record.reviewed_provenance
            and record.verification_status != "REJECTED"
            and record.source
            and record.source.verification_status != "REJECTED"
            for record in list_records(db, value.asset_id, "technical")
        )
        spatial_binding = bool(
            value.review
            and value.review.source_binding_confirmed
            and value.review.candidate_sha256 == candidate_digest(value)
        )
        if not existing_binding and not spatial_binding:
            raise ValueError("REVIEWED_EXACT_ASSET_SOURCE_BINDING_REQUIRED")
    return path


def review_check(value, issues, peer_assets):
    review = value.review
    if not review:
        return ["HUMAN_REFERENCE_REVIEW_REQUIRED"]
    failures = []
    if review.candidate_sha256 != candidate_digest(value):
        failures.append("REVIEW_CANDIDATE_HASH_MISMATCH")
    if review.reviewed_at > datetime.now(UTC):
        failures.append("REVIEW_DATE_IN_FUTURE")
    try:
        content = Path(review.evidence_path).read_bytes()
        if hashlib.sha256(content).hexdigest() != review.evidence_sha256:
            failures.append("REVIEW_RECEIPT_CHECKSUM_MISMATCH")
        receipt = HumanReview.model_validate(
            json.loads(content)
            | {
                "evidence_path": review.evidence_path,
                "evidence_sha256": review.evidence_sha256,
            }
        ).model_dump(mode="json", exclude={"evidence_path", "evidence_sha256"})
        expected = review.model_dump(
            mode="json", exclude={"evidence_path", "evidence_sha256"}
        )
        if receipt != expected:
            failures.append("REVIEW_RECEIPT_BINDING_MISMATCH")
    except (OSError, ValueError, TypeError):
        failures.append("REVIEW_RECEIPT_UNAVAILABLE")
    unresolved = set(issues) - set(review.resolved_conflicts)
    if unresolved or (issues and not review.conflict_resolution):
        failures.append("SOURCE_OR_COORDINATE_CONFLICT_REVIEW_REQUIRED")
    if peer_assets and (
        set(review.colocated_with) != set(peer_assets) or not review.colocation_basis
    ):
        failures.append("COLOCATION_REVIEW_REQUIRED")
    return failures


def _positions(db, candidates):
    positions = {}
    failures = {}
    for candidate in candidates:
        try:
            if candidate.coordinates:
                positions[candidate.candidate_id] = parse_coordinates(
                    candidate.coordinates, db
                )
        except ValueError as exc:
            failures[candidate.candidate_id] = str(exc)
    return positions, failures


def preflight(db, candidates, bundle):
    """Structured eligibility, preserving the distinction between candidate and accepted location."""
    positions, conversion_failures = _positions(db, candidates)
    rows = []
    for value in candidates:
        reasons, issues, peer_assets = [], list(value.conflicts), set()
        try:
            identity(db, value)
        except ValueError as exc:
            reasons.append(str(exc))
        try:
            source_check(db, value, require_asset_binding=True)
        except (OSError, ValueError, TypeError) as exc:
            reasons.append(str(exc))
        normalized = positions.get(value.candidate_id)
        if value.candidate_id in conversion_failures:
            reasons.append(
                "COORDINATE_CONVERSION_INVALID: "
                + conversion_failures[value.candidate_id]
            )
        if not normalized:
            reasons.append("EXPLICIT_SUPPORTED_CRS_COORDINATES_REQUIRED")
        if not value.review or not value.review.identity_confirmed:
            reasons.append("ASSET_IDENTITY_REVIEW_REQUIRED")
        if not value.source_id or not value.document_id:
            reasons.append("REGISTERED_SOURCE_DOCUMENT_BINDING_REQUIRED")
        existing = bundle["records"].get(str(value.asset_id))
        if normalized:
            point = normalized["geometry"]["coordinates"]
            reservoir_point = db.execute(
                select(
                    func.ST_X(Reservoir.location), func.ST_Y(Reservoir.location)
                ).where(Reservoir.id == value.reservoir_id)
            ).one_or_none()
            if (
                reservoir_point
                and None not in reservoir_point
                and distance_metres(point, reservoir_point) > 100_000
            ):
                issues.append("RESERVOIR_CONTEXT_DISTANCE_EXCEEDS_100KM")
            for other in candidates:
                if (
                    other.candidate_id == value.candidate_id
                    or other.candidate_id not in positions
                ):
                    continue
                distance = distance_metres(
                    point, positions[other.candidate_id]["geometry"]["coordinates"]
                )
                if other.asset_id != value.asset_id and distance <= 2:
                    peer_assets.add(other.asset_id)
                    issues.append(f"DUPLICATE_COORDINATE:{other.candidate_id}")
                    if other.source_sha256 == value.source_sha256:
                        issues.append(
                            f"DUPLICATE_SOURCE_COORDINATE:{other.candidate_id}"
                        )
                elif other.asset_id == value.asset_id and distance > 25:
                    issues.append(f"CONTRADICTORY_COORDINATE:{other.candidate_id}")
                if (
                    other.asset_id == value.parent_asset_id
                    or other.parent_asset_id == value.asset_id
                ) and distance <= 2:
                    issues.append(f"PARENT_CHILD_COLOCATION:{other.candidate_id}")
            for asset_id, approved in bundle["records"].items():
                geometry = approved["geometry"]
                if geometry["type"] != "Point":
                    continue
                distance = distance_metres(point, geometry["coordinates"])
                if asset_id != str(value.asset_id) and distance <= 2:
                    peer_assets.add(UUID(asset_id))
                    issues.append(f"COLOCATED_EXISTING_REFERENCE:{asset_id}")
                    other_asset = db.get(Asset, UUID(asset_id))
                    if str(value.parent_asset_id) == asset_id or (
                        other_asset and other_asset.parent_asset_id == value.asset_id
                    ):
                        issues.append(f"PARENT_CHILD_COLOCATION:{asset_id}")
            if existing and (
                existing["geometry"] != normalized["geometry"]
                or existing.get("evidence_id") != value.candidate_id
                or existing.get("source_sha256") != value.source_sha256
            ):
                reasons.append(
                    "EXISTING_REFERENCE_PROTECTED: explicit correction review is required; this command never overwrites"
                )
        issues = sorted(set(issues))
        reasons.extend(review_check(value, issues, peer_assets))
        if not reasons and existing:
            status = "UNCHANGED"
        else:
            status = "BLOCKED" if reasons else "ELIGIBLE"
        rows.append(
            {
                "candidate_id": value.candidate_id,
                "asset_id": str(value.asset_id),
                "asset_code": value.asset_code,
                "candidate_sha256": candidate_digest(value),
                "status": status,
                "reasons": reasons,
                "issues": issues,
                "normalized": normalized,
                "classification": "REFERENCE_LOCATION_ONLY",
            }
        )
    return rows


def merge_candidates(db, bundle, candidates, dispositions, *, validate_sources=True):
    """Stage pending evidence only. Never infer human approval or alter accepted records."""
    result = json.loads(json.dumps(bundle))
    old = {value["candidate_id"]: value for value in result.get("candidates", [])}
    for value in candidates:
        if validate_sources:
            identity(db, value)
            source_check(db, value)
        serialized = value.model_dump(mode="json")
        if value.candidate_id in old and old[value.candidate_id] != serialized:
            previous = SpatialCandidate.model_validate(old[value.candidate_id])
            if (
                candidate_digest(previous) != candidate_digest(value)
                or previous.review is not None
            ):
                raise ValueError(
                    "Candidate ID already binds different evidence/review; use a new revision ID"
                )
        old[value.candidate_id] = serialized
    all_candidates = [SpatialCandidate.model_validate(value) for value in old.values()]
    all_ids = {value.candidate_id: value for value in all_candidates}
    states = dict(result.get("dispositions", {}))
    for key, value in dispositions.items():
        identity(db, value)
        if any(
            candidate_id not in all_ids
            or all_ids[candidate_id].asset_id != value.asset_id
            for candidate_id in value.candidate_ids
        ):
            raise ValueError("Disposition candidate does not bind this exact asset")
        states[key] = value.model_dump(mode="json")
    result["candidates"] = [old[key] for key in sorted(old)]
    result["dispositions"] = states
    return result


def apply_candidates(db, bundle, candidates, selected):
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("Select explicit unique candidate IDs; no implicit bulk apply")
    by_id = {value.candidate_id: value for value in candidates}
    if not set(selected) <= set(by_id):
        raise ValueError("Unknown selected candidate ID")
    rows = {value["candidate_id"]: value for value in preflight(db, candidates, bundle)}
    if any(rows[key]["status"] == "BLOCKED" for key in selected):
        raise ValueError(
            "Selected candidates are blocked; inspect structured preflight reasons"
        )
    result = json.loads(json.dumps(bundle))
    for key in selected:
        value, row = by_id[key], rows[key]
        if row["status"] == "UNCHANGED":
            continue
        review = value.review
        entry = {
            "asset_id": str(value.asset_id),
            "reservoir_id": str(value.reservoir_id),
            "asset_code": value.asset_code,
            "location_status": "REFERENCE_LOCATION",
            "geometry": row["normalized"]["geometry"],
            "crs": "EPSG:4326",
            "source": value.source,
            "source_url": str(value.source_url) if value.source_url else None,
            "locator": value.locator,
            "evidence_id": value.candidate_id,
            "accuracy_limitation": value.accuracy_limitation,
            "verification_note": "Human-reviewed reference point for orientation only; not surveyed geometry. F02 unchanged.",
            "reviewer": review.reviewer,
            "reviewer_role": review.reviewer_role,
            "reviewed_at": review.reviewed_at.isoformat(),
            "coordinate_basis": value.coordinate_basis
            + "; "
            + row["normalized"]["method"],
            "estimated_accuracy_m": value.estimated_accuracy_m,
            "physical_page": value.physical_page,
            "document_id": str(value.document_id),
            "source_id": str(value.source_id),
            "source_sha256": value.source_sha256,
        }
        LocationReview.model_validate(entry)
        # This additional check prevents reassignment even when multiple selected candidates bind one asset.
        if str(value.asset_id) in result["records"]:
            if result["records"][str(value.asset_id)] != entry:
                raise ValueError(
                    "Existing reference is protected; no overwrite or reassignment"
                )
        else:
            result["records"][str(value.asset_id)] = entry
    return result, [rows[key] for key in selected]


@contextmanager
def locked_path(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def atomic_write(path, value):
    with NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    try:
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def add_candidate(db, args):
    required = (
        "asset",
        "original",
        "source_label",
        "source_title",
        "page",
        "locator",
        "basis",
        "identity_basis",
        "limitation",
        "next_action",
        "candidate_id",
        "output",
    )
    if any(getattr(args, key) is None for key in required):
        raise ValueError(
            "add-candidate requires --asset --original --source-label --source-title --page --locator --basis --identity-basis --limitation --next-action --candidate-id --output"
        )
    asset = db.get(Asset, UUID(args.asset))
    if not asset:
        raise ValueError("Unknown asset UUID")
    original = args.original.resolve(strict=True)
    coordinates = coordinate_arguments(args)
    value = SpatialCandidate(
        candidate_id=args.candidate_id,
        asset_id=asset.id,
        reservoir_id=asset.reservoir_id,
        asset_code=asset.asset_code,
        parent_asset_id=asset.parent_asset_id,
        source_label=args.source_label,
        source=args.source_title,
        source_url=args.source_url,
        source_id=args.source_id,
        document_id=args.document,
        original_path=str(original),
        source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        physical_page=args.page,
        locator=args.locator,
        coordinates=coordinates,
        coordinate_basis=args.basis,
        identity_basis=args.identity_basis,
        accuracy_limitation=args.limitation,
        next_action=args.next_action,
    )
    identity(db, value)
    source_check(db, value)
    if coordinates:
        parse_coordinates(coordinates, db)
    packet = {"version": 1, "candidates": [], "dispositions": {}}
    if args.output.exists():
        previous, dispositions = load_packet(args.output)
        if any(item.candidate_id == value.candidate_id for item in previous):
            raise ValueError("Candidate ID already exists in packet")
        packet = {
            "version": 1,
            "candidates": [item.model_dump(mode="json") for item in previous],
            "dispositions": {
                key: item.model_dump(mode="json") for key, item in dispositions.items()
            },
        }
    packet["candidates"].append(value.model_dump(mode="json"))
    if args.apply:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(args.output, packet)
    return {
        "action": "add-candidate",
        "write_applied": args.apply,
        "candidate_id": value.candidate_id,
        "candidate_sha256": candidate_digest(value),
        "classification": "UNAPPROVED_CANDIDATE_ONLY",
        "packet": str(args.output),
    }


def coordinate_arguments(args):
    direct = [args.source_crs, args.axis_order, args.coordinate_format, args.x, args.y]
    if args.coordinates:
        if any(value is not None for value in direct):
            raise ValueError(
                "Choose a coordinate JSON or explicit coordinate flags, not both"
            )
        return CoordinateInput.model_validate_json(args.coordinates.read_text())
    if not any(value is not None for value in direct):
        return None
    if any(value is None for value in direct):
        raise ValueError(
            "Coordinates require --source-crs --axis-order --coordinate-format --x --y"
        )
    return CoordinateInput(
        source_crs=args.source_crs,
        axis_order=args.axis_order,
        format=args.coordinate_format,
        x=args.x,
        y=args.y,
    )


def set_disposition(db, args):
    if (
        not args.asset
        or not args.output
        or not args.disposition_status
        or not args.reason
        or not args.next_action
    ):
        raise ValueError(
            "set-disposition requires --asset --output --disposition-status --reason --next-action"
        )
    asset = db.get(Asset, UUID(args.asset))
    if not asset:
        raise ValueError("Unknown asset UUID")
    candidates, dispositions = (
        load_packet(args.output) if args.output.exists() else ([], {})
    )
    value = SpatialDisposition(
        asset_id=asset.id,
        reservoir_id=asset.reservoir_id,
        asset_code=asset.asset_code,
        status=args.disposition_status,
        reason=args.reason,
        next_action=args.next_action,
        candidate_ids=args.candidate,
    )
    identity(db, value)
    by_id = {item.candidate_id: item for item in candidates}
    if any(
        key not in by_id or by_id[key].asset_id != asset.id for key in args.candidate
    ):
        raise ValueError(
            "Disposition candidates must already exist in this packet and bind this asset"
        )
    dispositions[str(asset.id)] = value
    packet = {
        "version": 1,
        "candidates": [item.model_dump(mode="json") for item in candidates],
        "dispositions": {
            key: item.model_dump(mode="json") for key, item in dispositions.items()
        },
    }
    if args.apply:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(args.output, packet)
    return {
        "action": "set-disposition",
        "write_applied": args.apply,
        "asset_id": str(asset.id),
        "status": value.status,
        "classification": "UNAPPROVED_DISPOSITION_ONLY",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "preflight",
            "stage",
            "apply",
            "parse",
            "template",
            "add-candidate",
            "attach-review",
            "set-disposition",
        ],
    )
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--sidecar", type=Path, default=default_path())
    parser.add_argument("--candidate", action="append", default=[])
    parser.add_argument(
        "--apply", action="store_true", help="Explicit write; omitted means dry-run"
    )
    parser.add_argument(
        "--coordinates", type=Path, help="CoordinateInput JSON; parse only"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-crs", choices=["EPSG:4326", "EPSG:32648"])
    parser.add_argument(
        "--axis-order",
        choices=["longitude_latitude", "latitude_longitude", "easting_northing"],
    )
    parser.add_argument("--coordinate-format", choices=["decimal", "dms", "utm"])
    parser.add_argument("--x")
    parser.add_argument("--y")
    parser.add_argument(
        "--disposition-status",
        choices=["CANDIDATE_NEEDS_REVIEW", "CONFLICTED", "NO_DEFENSIBLE_LOCATION"],
    )
    parser.add_argument("--reason")
    parser.add_argument("--asset")
    parser.add_argument("--original", type=Path)
    parser.add_argument("--source-label")
    parser.add_argument("--source-title")
    parser.add_argument("--source-url")
    parser.add_argument("--source-id")
    parser.add_argument("--document")
    parser.add_argument("--page", type=int)
    parser.add_argument("--locator")
    parser.add_argument("--basis")
    parser.add_argument("--identity-basis")
    parser.add_argument("--limitation")
    parser.add_argument("--next-action")
    parser.add_argument("--candidate-id")
    parser.add_argument("--review-receipt", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "template":
            if not args.output:
                parser.error("template requires --output")
            if args.output.exists():
                raise ValueError("Template output already exists; refusing overwrite")
            if args.apply:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(
                    args.output, {"version": 1, "candidates": [], "dispositions": {}}
                )
            print(
                json.dumps(
                    {
                        "status": "CREATED_EMPTY_TEMPLATE"
                        if args.apply
                        else "WOULD_CREATE_EMPTY_TEMPLATE",
                        "write_applied": args.apply,
                        "output": str(args.output),
                    }
                )
            )
            return
        with SessionLocal() as db:
            if args.action in ("add-candidate", "set-disposition"):
                operation = (
                    add_candidate if args.action == "add-candidate" else set_disposition
                )
                if args.apply and args.output:
                    with locked_path(args.output):
                        report = operation(db, args)
                else:
                    report = operation(db, args)
            elif args.action == "parse":
                coordinates = coordinate_arguments(args)
                if coordinates is None:
                    raise ValueError(
                        "parse requires explicit coordinate flags or --coordinates JSON"
                    )
                report = parse_coordinates(coordinates, db)
            else:
                if args.packet:
                    incoming, dispositions = load_packet(args.packet)
                else:
                    incoming, dispositions = [], {}

                # Lock applies to mutation and read-validate-write; preflight leaves no lock file.
                def operation():
                    bundle = read_bundle(args.sidecar)
                    if args.action == "attach-review":
                        if len(args.candidate) != 1 or not args.review_receipt:
                            raise ValueError(
                                "attach-review requires one --candidate and --review-receipt"
                            )
                        content = args.review_receipt.read_bytes()
                        receipt = json.loads(content)
                        review = HumanReview.model_validate(
                            receipt
                            | {
                                "evidence_path": str(args.review_receipt.resolve()),
                                "evidence_sha256": hashlib.sha256(content).hexdigest(),
                            }
                        )
                        current = next(
                            (
                                SpatialCandidate.model_validate(item)
                                for item in bundle.get("candidates", [])
                                if item["candidate_id"] == args.candidate[0]
                            ),
                            None,
                        )
                        if current is None:
                            raise ValueError("Unknown candidate ID")
                        current.review = review
                        receipt_failures = review_check(current, [], set())
                        if receipt_failures or not review.identity_confirmed:
                            raise ValueError(
                                "Review receipt cannot bind this candidate: "
                                + ", ".join(
                                    receipt_failures
                                    or ["ASSET_IDENTITY_REVIEW_REQUIRED"]
                                )
                            )
                        incoming.append(current)
                    merged = (
                        merge_candidates(
                            db,
                            bundle,
                            incoming,
                            dispositions,
                            validate_sources=args.action != "preflight",
                        )
                        if args.packet or args.action == "attach-review"
                        else bundle
                    )
                    candidates = [
                        SpatialCandidate.model_validate(value)
                        for value in merged.get("candidates", [])
                    ]
                    rows = preflight(db, candidates, merged)
                    if args.action == "apply":
                        changed, selected = apply_candidates(
                            db, merged, candidates, args.candidate
                        )
                    else:
                        changed, selected = merged, rows
                    report = {
                        "action": args.action,
                        "write_applied": args.apply
                        and args.action in ("stage", "apply", "attach-review"),
                        "accepted_before": len(bundle["records"]),
                        "accepted_after": len(changed["records"]),
                        "candidate_count": len(candidates),
                        "candidates": selected,
                        "sidecar_changed": changed != bundle,
                    }
                    if (
                        args.apply
                        and args.action in ("stage", "apply", "attach-review")
                        and changed != bundle
                    ):
                        atomic_write(args.sidecar, changed)
                    return report

                if args.apply and args.action in ("stage", "apply", "attach-review"):
                    with locked_path(args.sidecar):
                        report = operation()
                else:
                    report = operation()
            # stdout is private: normalized candidate coordinates are intentionally absent from public API.
            print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Reference workflow refused: {exc}\n")


if __name__ == "__main__":
    main()
