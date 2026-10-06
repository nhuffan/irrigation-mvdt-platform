"""Deterministic metrics from a frozen snapshot, never from mutable live seed data."""

import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

from scripts.research_common import KINDS, load_snapshot, write_csv


def ratio(n, d):
    return {
        "numerator": n,
        "denominator": d,
        "value": n / d if d else None,
        "status": "MEASURED" if d else "NOT_APPLICABLE_OR_NO_DENOMINATOR",
    }


def has_value(r):
    return r.get("value_number") is not None or bool(
        (r.get("value_text") or "").strip()
    )


def evaluate(s):
    scope = s["scope"]
    assets = s["assets"]
    verified = [a for a in assets if a["data_status"] == "VERIFIED"]
    ids = {a["id"] for a in verified}
    by_id = {a["id"]: a for a in assets}
    source_by_id = {r["id"]: r for r in s["sources"]}
    records = [r for kind in KINDS for r in s["records"][kind]]
    per_kind = {kind: defaultdict(list) for kind in KINDS}
    for kind in KINDS:
        for r in s["records"][kind]:
            per_kind[kind][r["asset_id"]].append(r)
    present = {
        kind: {
            aid
            for aid, rs in per_kind[kind].items()
            if any(
                (has_value(r) if kind == "technical" else True)
                and (
                    r["verification_status"] == "VERIFIED"
                    if kind in ("technical", "conditions")
                    else True
                )
                for r in rs
            )
        }
        for kind in KINDS
    }
    metrics = {
        "asset_identification": ratio(len(verified), len(scope["target_asset_codes"])),
        "gis_mapping": ratio(
            sum(a["usable_geometry"] for a in verified), len(verified)
        ),
    }
    for kind in KINDS:
        metrics[kind + "_coverage"] = ratio(len(present[kind] & ids), len(ids))
    linked = [r for r in records if r.get("source_id") in source_by_id]
    metrics["source_traceability"] = ratio(len(linked), len(records))
    metrics["verified_source_records"] = ratio(
        sum(
            source_by_id[r["source_id"]]["verification_status"] == "VERIFIED"
            for r in linked
        ),
        len(linked),
    )
    metrics["verified_record_ratio"] = ratio(
        sum(r["verification_status"] == "VERIFIED" for r in records), len(records)
    )
    expected = set(scope["expected_document_source_codes"])
    accessible = {
        source_by_id[d["source_id"]]["source_code"]
        for d in s["documents"]
        if d["file_evidence"]["accessible"]
    }
    metrics["document_coverage"] = ratio(len(expected & accessible), len(expected))
    docs = s["documents"]
    metrics["document_integrity"] = ratio(
        sum(d["file_evidence"].get("checksum_matches") is True for d in docs), len(docs)
    )
    models = {m["id"]: m for m in s["models"]}
    links = s["model_asset_links"]
    resolved = []
    for link in links:
        evidence = models[link["model_id"]]["file_evidence"]
        if (
            link["object_key"] in evidence.get("object_keys", [])
            and link["object_key"] not in evidence.get("ambiguous_object_keys", [])
            and link["verification_status"] != "REJECTED"
        ):
            resolved.append(link)
    represented = {
        by_id[l["asset_id"]]["asset_code"] for l in resolved if l["asset_id"] in ids
    }
    target3d = set(scope["three_d_asset_codes"])
    metrics["three_d_coverage"] = ratio(len(represented & target3d), len(target3d))
    metrics["mapping_verification"] = ratio(
        sum(l["verification_status"] == "VERIFIED" for l in links), len(links)
    )
    completeness = []
    missing = []
    for code in scope["target_asset_codes"]:
        a = next((a for a in assets if a["asset_code"] == code), None)
        aid = a["id"] if a else None
        flags = {
            "identity": bool(a and a["name"]),
            "category": bool(a and a.get("category_id")),
            "spatial": bool(a and a["usable_geometry"]),
            "technical": aid in present["technical"],
            "condition": aid in present["conditions"],
            "inspection": aid in present["inspections"],
            "repair": aid in present["repairs"],
            "maintenance": aid in present["maintenance"],
            "source": any(r["asset_id"] == aid for r in linked),
        }
        required = [
            f
            for f in scope["maim_required"]
            if f not in scope.get("not_applicable", {}).get(code, {})
        ]
        for field in required:
            if not flags[field]:
                missing.append({"asset_code": code, "field": field})
        completeness.append(
            {
                "asset_code": code,
                "available": sum(flags[f] for f in required),
                "required": len(required),
                "value": sum(flags[f] for f in required) / len(required)
                if required
                else None,
            }
        )
    values = [r["value"] for r in completeness if r["value"] is not None]
    groups = defaultdict(list)
    for r in s["records"]["technical"]:
        groups[(r["asset_id"], r["attribute_key"])].append(r)
    conflicts = []
    evaluated = 0
    for (aid, key), rs in groups.items():
        vals = {
            (r.get("value_number"), (r.get("value_text") or "").strip(), r.get("unit"))
            for r in rs
            if has_value(r)
        }
        if vals:
            evaluated += 1
        if len(vals) > 1:
            conflicts.append(
                {
                    "asset_code": by_id[aid]["asset_code"],
                    "attribute_key": key,
                    "distinct_values": len(vals),
                    "record_ids": "|".join(r["id"] for r in rs),
                    "resolution": "UNREVIEWED",
                }
            )
    metrics["technical_conflict_rate"] = ratio(len(conflicts), evaluated)
    known_dates = sum(bool(r.get("source_date")) for r in s["sources"])
    metrics["source_date_known"] = ratio(known_dates, len(s["sources"]))
    return {
        "dataset_version": scope["dataset_version"],
        "metrics": metrics,
        "completeness_summary": {
            "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        },
        "completeness": completeness,
        "missing_fields": missing,
        "conflicts": conflicts,
        "unlinked_objects": [
            {"model_id": m["id"], "object_key": key}
            for m in s["models"]
            for key in m["file_evidence"].get("object_keys", [])
            if not any(
                l["model_id"] == m["id"] and l["object_key"] == key for l in links
            )
        ],
        "limitations": [
            "Coverage is scoped to the approved inventory and explicit record IDs.",
            "O&M absence does not prove that no work occurred.",
            "Technical conflicts are candidate conflicts; units/dates require domain review.",
            "Known source date is not a freshness/currentness judgement.",
            "Retrieval improvement and usability require actual participant observations.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot, sha = load_snapshot(args.snapshot)
    # Validate retained evidence, independently of the original storage path.
    import hashlib

    for media in [*snapshot["documents"], *snapshot["models"]]:
        e = media["file_evidence"]
        if e["accessible"]:
            if not re.fullmatch(r"[0-9a-f]{64}", e.get("sha256") or ""):
                raise ValueError("Invalid frozen file checksum")
            expected = args.snapshot.parent / "files" / e["sha256"]
            if hashlib.sha256(expected.read_bytes()).hexdigest() != e["sha256"]:
                raise ValueError("Frozen file checksum mismatch")
    result = evaluate(snapshot)
    result["snapshot_sha256"] = sha
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "evaluation_results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )
    rows = [{"metric": key, **value} for key, value in result["metrics"].items()]
    write_csv(
        args.output / "coverage_metrics.csv",
        rows,
        ["metric", "numerator", "denominator", "value", "status"],
    )
    for name, fields in [
        ("completeness", ["asset_code", "available", "required", "value"]),
        ("missing_fields", ["asset_code", "field"]),
        (
            "conflicts",
            [
                "asset_code",
                "attribute_key",
                "distinct_values",
                "record_ids",
                "resolution",
            ],
        ),
        ("unlinked_objects", ["model_id", "object_key"]),
    ]:
        write_csv(args.output / (name + ".csv"), result[name], fields)
    write_csv(
        args.output / "asset_inventory.csv",
        snapshot["assets"],
        [
            "asset_code",
            "name",
            "category_name",
            "parent_asset_id",
            "data_status",
            "usable_geometry",
        ],
    )
    write_csv(
        args.output / "data_sources.csv",
        snapshot["sources"],
        ["source_code", "title", "source_type", "source_date", "verification_status"],
    )
    for name, keys in {
        "om_coverage": [
            "conditions_coverage",
            "inspections_coverage",
            "repairs_coverage",
            "maintenance_coverage",
        ],
        "document_coverage": ["document_coverage", "document_integrity"],
        "model_link_coverage": ["three_d_coverage", "mapping_verification"],
    }.items():
        write_csv(
            args.output / (name + ".csv"),
            [r for r in rows if r["metric"] in keys],
            ["metric", "numerator", "denominator", "value", "status"],
        )
    quality = [
        {
            "dimension": "Completeness",
            "method": "Mean applicable MAIM coverage",
            "value": result["completeness_summary"]["mean"],
            "caveat": "Presence and verification rules are field-specific",
        },
        {
            "dimension": "Consistency",
            "method": "Technical candidate conflict rate",
            "value": result["metrics"]["technical_conflict_rate"]["value"],
            "caveat": "Requires unit and temporal review; not automatically incorrect",
        },
        {
            "dimension": "Reliability",
            "method": "Source-linked records with VERIFIED source",
            "value": result["metrics"]["verified_source_records"]["value"],
            "caveat": "Database verification status is not independent source authentication",
        },
        {
            "dimension": "Freshness",
            "method": "Source date known",
            "value": result["metrics"]["source_date_known"]["value"],
            "caveat": "Currentness threshold has not been established",
        },
        {
            "dimension": "Traceability",
            "method": "Technical/O&M source-link rate",
            "value": result["metrics"]["source_traceability"]["value"],
            "caveat": "Source metadata does not establish accessible file evidence",
        },
    ]
    write_csv(
        args.output / "data_quality.csv",
        quality,
        ["dimension", "method", "value", "caveat"],
    )
    print(f"Evaluated {result['dataset_version']} from snapshot {sha}")


if __name__ == "__main__":
    main()
