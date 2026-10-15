"""Export paper Tables 1/4/6 from archived DB, API readback and controlled inputs.

No database writes. Counts are implementation evidence, not methodology approval.
API readback must be captured against the same unchanged database/media snapshot.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path

RECORDS = ("technical", "conditions", "inspections", "repairs", "maintenance")


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def build_tables(snapshot, api, targets, sources, doc_reviews, acceptance):
    rows = snapshot["rows"]
    codes = {r["target_asset_code"] for r in targets if r["in_scope"] == "true"}
    assets = {r["asset_code"]: r for r in rows["assets"] if r["asset_code"] in codes}
    if set(assets) != codes or set(api) != codes:
        raise ValueError(
            "Snapshot/API must cover exactly the controlled in-scope targets"
        )
    source_codes = {r["source_code"] for r in sources}
    source_ids = {
        r["id"] for r in rows["data_sources"] if r["source_code"] in source_codes
    }
    retained = {
        r["checksum_sha256"] for r in doc_reviews if r["document_status"] == "IMPORT"
    }
    # Count files physically retained in the DB, not unfulfilled review intentions.
    retained &= {
        r["checksum_sha256"]
        for r in rows["documents"]
        if snapshot["storage_sha256"].get(r["storage_key"]) == r["checksum_sha256"]
    }
    per_asset = []
    for code, asset in sorted(assets.items()):
        payload = api[code]
        if payload["asset"]["id"] != asset["id"]:
            raise ValueError("API asset identity mismatch")
        records = {
            kind: [r for r in rows[kind] if r["asset_id"] == asset["id"]]
            for kind in RECORDS
        }
        tech = {r["id"]: r for r in records["technical"]}
        if {r["id"] for r in payload["technical"]} != set(tech):
            raise ValueError("Technical readback mismatch")
        l2 = 0
        for record in payload["technical"]:
            if any(
                record[k] != tech[record["id"]][k]
                for k in (
                    "asset_id",
                    "source_id",
                    "attribute_key",
                    "attribute_label",
                    "value_number",
                    "value_text",
                    "unit",
                    "verification_status",
                )
            ):
                raise ValueError("Stale technical readback")
            provenance = record.get("reviewed_provenance")
            l2 += bool(provenance and provenance["verification_level"] == "L2")
        linked_sources = {
            r["source_id"]
            for values in records.values()
            for r in values
            if r.get("source_id")
        }
        linked_docs = [d for d in rows["documents"] if d["source_id"] in linked_sources]
        if {d["id"] for d in payload["documents"]} != {d["id"] for d in linked_docs}:
            raise ValueError("Source-derived document readback mismatch")
        location = payload["asset"].get("location") or {}
        condition = payload["current-condition"]
        per_asset.append(
            {
                "asset_code": code,
                "asset_id": asset["id"],
                "technical_l2": l2,
                "linked_controlled_sources": len(linked_sources & source_ids),
                "linked_document_records": len(linked_docs),
                "linked_distinct_sha256": len(
                    {d["checksum_sha256"] for d in linked_docs}
                ),
                "reference_locations": int(
                    location.get("location_status") == "REFERENCE_LOCATION"
                ),
                "canonical_geometry_present": int(asset["geometry"] is not None),
                "verified_current_condition": int(
                    bool(condition and condition["verification_status"] == "VERIFIED")
                ),
                "verified_om_records": sum(
                    r["verification_status"] == "VERIFIED"
                    for kind in RECORDS[1:]
                    for r in records[kind]
                ),
                "representative_3d_links": sum(
                    r["asset_id"] == asset["id"]
                    and r["verification_status"] == "VERIFIED"
                    for r in rows["model_asset_links"]
                ),
            }
        )
    metrics = [
        ("RS assets", len(assets), "controlled in-scope target IDs"),
        (
            "Controlled sources",
            len(sources),
            "inventory rows; not per-asset sum or authority claim",
        ),
        (
            "Expected-file sources",
            sum(r["file_expected"] == "true" for r in sources),
            "file_expected=true",
        ),
        (
            "Distinct retained reviewed docs",
            len(retained),
            "unique SHA256 physically retained and IMPORT-reviewed",
        ),
    ]
    for key, definition in [
        ("technical_l2", "API-bound L2 provenance; no candidate rows"),
        (
            "linked_document_records",
            "sum of source-derived asset-document edges, not unique files",
        ),
        (
            "reference_locations",
            "reference-only assets; excluded from canonical numerator",
        ),
        (
            "canonical_geometry_present",
            "DB geometry present; presence alone does not certify accuracy",
        ),
        ("verified_current_condition", "latest VERIFIED condition returned by API"),
        (
            "verified_om_records",
            "condition/inspection/repair/maintenance records, not distinct activities",
        ),
        (
            "representative_3d_links",
            "VERIFIED link records; representative LOCAL, not surveyed identity",
        ),
    ]:
        metrics.append((key, sum(r[key] for r in per_asset), definition))
    metrics.append(
        (
            "Selected 3D targets",
            sum(
                r.get("requires_3d") == "true"
                for r in targets
                if r["target_asset_code"] in codes
            ),
            "controlled requires_3d target count; not full-asset coverage",
        )
    )
    table1 = [{"metric": m, "count": n, "definition": d} for m, n, d in metrics]
    # Retain all controlled rows and exact dates; never turn a fresh API check into browser PASS.
    table6 = [
        {
            k: r[k]
            for k in (
                "check_id",
                "function",
                "dataset_version",
                "status",
                "checked_at",
                "evidence_reference",
                "reviewer",
                "notes",
            )
        }
        for r in acceptance
    ]
    return table1, per_asset, table6


def write_table(path, rows):
    keys = list(rows[0])
    with path.with_suffix(".csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    path.with_suffix(".md").write_text(
        "| "
        + " | ".join(keys)
        + " |\n|"
        + "|".join("---" for _ in keys)
        + "|\n"
        + "".join(
            "| " + " | ".join(cell(row[k]) for k in keys) + " |\n" for row in rows
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot", "api-readback", "controlled-dir", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    inputs = [args.snapshot, args.api_readback] + [
        args.controlled_dir / name
        for name in (
            "target_assets.csv",
            "source_inventory.csv",
            "document_review.csv",
            "functional_validation.csv",
        )
    ]
    snapshot = json.loads(args.snapshot.read_text())
    tables = build_tables(
        snapshot,
        json.loads(args.api_readback.read_text()),
        *(read_csv(path) for path in inputs[2:]),
    )
    args.output.mkdir(parents=True, exist_ok=True)
    for name, table in zip(
        (
            "table_1_baseline",
            "table_4_asset_integration",
            "table_6_functional_acceptance",
        ),
        tables,
    ):
        write_table(args.output / name, table)
    (args.output / "manifest.json").write_text(
        json.dumps(
            {
                "database_fingerprint": snapshot["database_fingerprint"],
                "inputs": {
                    str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in inputs
                },
                "limitations": [
                    "Controlled acceptance retains original checked_at and scope.",
                    "Canonical presence is not proof of accuracy.",
                    "Candidate sources/attributes are excluded.",
                    "Per-asset source/doc counts overlap; do not sum for distinct totals.",
                ],
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
