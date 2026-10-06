"""Explicit research scope and immutable, checksummed evidence helpers."""

import csv
import hashlib
import json
from pathlib import Path

KINDS = ("technical", "conditions", "inspections", "repairs", "maintenance")
FIELDS = (
    "identity",
    "category",
    "spatial",
    "technical",
    "condition",
    "inspection",
    "repair",
    "maintenance",
    "source",
)


def canonical(data):
    return json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode()


def digest(data):
    return hashlib.sha256(canonical(data)).hexdigest()


def research_code(value):
    return isinstance(value, str) and value.startswith("RS-") and len(value) > 3


def validate_scope(scope):
    if scope.get("data_origin") != "RESEARCH":
        raise ValueError("Research scope must explicitly declare RESEARCH origin")
    for key in ("dataset_version", "reviewed_by", "inventory_reference", "as_of_date"):
        if not isinstance(scope.get(key), str) or not scope[key].strip():
            raise ValueError(f"Missing approved scope field: {key}")
    from datetime import date

    date.fromisoformat(scope["as_of_date"])
    for key in (
        "target_asset_codes",
        "source_codes",
        "expected_document_source_codes",
        "three_d_asset_codes",
    ):
        values = scope.get(key)
        if (
            not isinstance(values, list)
            or len(values) != len(set(values))
            or not all(research_code(x) for x in values)
        ):
            raise ValueError(f"{key} must contain unique RS- research codes")
    if not scope["target_asset_codes"]:
        raise ValueError(
            "Verified Phase 1 target inventory is required; no invented denominator"
        )
    if not set(scope["expected_document_source_codes"]) <= set(scope["source_codes"]):
        raise ValueError("Document expectation must be in source scope")
    if not set(scope["three_d_asset_codes"]) <= set(scope["target_asset_codes"]):
        raise ValueError("3D target must be in asset scope")
    if (
        not scope.get("maim_required")
        or not set(scope["maim_required"]) <= set(FIELDS)
        or len(scope["maim_required"]) != len(set(scope["maim_required"]))
    ):
        raise ValueError("Explicit unique MAIM required fields are required")
    for code, exceptions in scope.get("not_applicable", {}).items():
        if (
            code not in scope["target_asset_codes"]
            or not set(exceptions) <= set(scope["maim_required"])
            or not all(isinstance(v, str) and v.strip() for v in exceptions.values())
        ):
            raise ValueError(
                "N/A fields require an in-scope asset and written rationale"
            )
    from uuid import UUID

    for key in (*KINDS, "documents", "models", "model_asset_links"):
        ids = scope.get("record_ids", {}).get(key)
        if not isinstance(ids, list) or len(ids) != len(set(ids)):
            raise ValueError(f"Explicit unique record IDs required: {key}")
        for value in ids:
            UUID(value)
    if not isinstance(scope.get("reservoir_ids"), list) or not scope["reservoir_ids"]:
        raise ValueError("Included reservoirs must be explicitly listed")
    for value in scope["reservoir_ids"]:
        UUID(value)
    return scope


def load_snapshot(path):
    package = json.loads(Path(path).read_text())
    if package.get("sha256") != digest(package.get("snapshot")):
        raise ValueError("Snapshot checksum mismatch")
    validate_scope(package["snapshot"]["scope"])
    return package["snapshot"], package["sha256"]


def write_csv(path, rows, columns):
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
