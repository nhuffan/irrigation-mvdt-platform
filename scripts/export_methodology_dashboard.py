"""Publish a minimal, sanitized methodology snapshot; never write to the database.

Run with the API's Python environment from the repository root after capturing
DB/API readback. Reuses the validated Tables 1/4/6 exporter and readiness compiler.
Private originals, source notes, reviewer receipts and paths are never published.
"""

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
sys.path.insert(0, str(ROOT / "scripts"))
from export_asset_evidence_tables import (
    build_tables,
    read_csv,
    write_table,
)
from scripts.methodology_review import load_methodology
from scripts.prepare_empirical_scope import compile_scope, read_rows


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(snapshot_path, api_path, controlled, output, public):
    snapshot = json.loads(snapshot_path.read_text())
    api = json.loads(api_path.read_text())
    base = json.loads((controlled / "base-scope.json").read_text())
    targets, sources, documents, acceptance = [
        read_csv(controlled / name)
        for name in (
            "target_assets.csv",
            "source_inventory.csv",
            "document_review.csv",
            "functional_validation.csv",
        )
    ]
    tables = build_tables(
        snapshot,
        api,
        targets,
        sources,
        documents,
        acceptance,
        base.get("component_scope"),
    )
    output.mkdir(parents=True, exist_ok=True)
    for name, table in zip(
        (
            "table_1_baseline",
            "table_4_asset_integration",
            "table_6_functional_acceptance",
        ),
        tables,
    ):
        write_table(output / name, table)
    report, _ = compile_scope(
        base,
        targets,
        sources,
        read_rows(controlled / "maim_requirements.csv"),
        json.loads((controlled / "case_study_review.json").read_text()),
        acceptance,
        applicability=read_csv(controlled / "fv_applicability_review.csv"),
        methodology=load_methodology(controlled / "methodology_review.json"),
    )
    (output / "readiness.json").write_text(json.dumps(report, indent=2) + "\n")
    rows = snapshot["rows"]
    live_sources = {s["source_code"]: s for s in rows["data_sources"]}
    source_reviews = {
        s["source_code"]: s for s in read_csv(controlled / "source_review.csv")
    }
    admitted_ids = {
        live_sources[s["source_code"]]["id"]
        for s in sources
        if s["source_code"] in live_sources
    }
    retained_docs = [
        d
        for d in rows["documents"]
        if d["source_id"] in admitted_ids
        and snapshot["storage_sha256"].get(d["storage_key"]) == d["checksum_sha256"]
    ]
    asset_rows = []
    for a in tables[1]:
        if a["asset_code"].startswith("TOTAL:"):
            continue
        p = api[a["asset_code"]]
        tech = p["technical"]
        if any(
            not t.get("reviewed_provenance")
            or t["reviewed_provenance"]["verification_level"] != "L2"
            for t in tech
        ):
            raise ValueError(
                "Technical rows without reviewed L2 require explicit reporting"
            )
        asset_rows.append(
            {
                **a,
                "name": p["asset"]["name"],
                "technical_ids": sorted(t["id"] for t in tech),
                "technical_readback": [
                    {
                        "id": t["id"],
                        "key": t["attribute_key"],
                        "number": t["value_number"],
                        "text": t["value_text"],
                        "unit": t["unit"],
                        "verification_status": t["verification_status"],
                        "source_id": t["source_id"],
                        "level": t["reviewed_provenance"]["verification_level"],
                        "locator": t["reviewed_provenance"]["source_locator"],
                        "source_code": t["reviewed_provenance"]["source_code"],
                        "authority": t["reviewed_provenance"]["authority"],
                    }
                    for t in sorted(tech, key=lambda t: t["id"])
                ],
                "document_ids": sorted(d["id"] for d in p["documents"]),
                "location_status": (p["asset"].get("location") or {}).get(
                    "location_status", "UNKNOWN"
                ),
                "provenance": [
                    {
                        "source_code": t["reviewed_provenance"]["source_code"],
                        "locator": t["reviewed_provenance"]["source_locator"],
                        "authority": t["reviewed_provenance"]["authority"],
                        "attribute_key": t["attribute_key"],
                    }
                    for t in tech
                ],
            }
        )
    # Evidence references are labels and hashes only: no raw receipt or file route.
    functions = []
    for row in tables[2]:
        evidence = []
        for ref in row["evidence_reference"].split(";"):
            ref = ref.strip()
            path = ROOT / "research/evaluation" / ref
            evidence.append(
                {
                    "label": Path(ref).name,
                    "sha256": sha(path) if path.is_file() else None,
                }
            )
        functions.append(
            {
                k: row[k]
                for k in (
                    "check_id",
                    "function",
                    "dataset_version",
                    "status",
                    "checked_at",
                )
            }
            | {"evidence": evidence}
        )
    files = {
        p.name: sha(p)
        for p in controlled.iterdir()
        if p.is_file() and p.suffix in (".csv", ".json")
    }
    protocols = {
        "tasks": [
            {"id": f"T{i}", "prompt": prompt}
            for i, prompt in enumerate(
                [
                    "Locate the latest inspection.",
                    "Find the latest verified condition.",
                    "Identify the document supporting a maintenance record.",
                    "Find all scoped repairs.",
                    "Locate the asset using reviewed GIS evidence.",
                    "Identify its linked 3D object or state no mapping.",
                ],
                1,
            )
        ],
        "retrieval_fields": next(
            csv.reader(
                (
                    ROOT / "research/evaluation/templates/retrieval_observations.csv"
                ).open()
            )
        ),
        "answer_key_fields": next(
            csv.reader(
                (ROOT / "research/evaluation/templates/retrieval_answer_key.csv").open()
            )
        ),
        "questionnaire_fields": next(
            csv.reader(
                (
                    ROOT / "research/evaluation/templates/usability_observations.csv"
                ).open()
            )
        ),
        "questionnaire": [
            "Asset information was easy to locate.",
            "GIS helped explain asset location.",
            "O&M history was easy to follow.",
            "Source/document linkage improved traceability.",
            "3D helped explain asset context.",
            "The system could support routine O&M information retrieval.",
            "The interface was understandable.",
            "I would prefer this workflow over fragmented file search.",
        ],
        "collection_status": "NOT_COLLECTED",
        "results": None,
    }
    payload = {
        "schema_version": "METHODOLOGY-DASHBOARD-v1",
        "dataset_version": base["dataset_version"],
        "reservoir_id": base["reservoir_ids"][0],
        "captured_at": snapshot["captured_at"],
        "database_fingerprint": snapshot["database_fingerprint"],
        "methodology": {
            "status": report["status"],
            "dataset_status": "NOT_FROZEN"
            if report["status"] != "READY"
            else "NOT_ASSESSED",
            "fingerprint": report["methodology_package_sha256"],
            "unresolved_gate_count": len(report["blockers"]),
            "as_of_date": base.get("as_of_date") or None,
        },
        "assets": asset_rows,
        "sources": [
            {
                "id": live_sources.get(s["source_code"], {}).get("id"),
                "code": s["source_code"],
                "expected_file": s["file_expected"] == "true",
                "verification_status": live_sources.get(s["source_code"], {}).get(
                    "verification_status", "NOT_ADMITTED"
                ),
                "authority": source_reviews.get(s["source_code"], {}).get(
                    "authority_class"
                )
                or "UNKNOWN",
                "review_status": source_reviews.get(s["source_code"], {}).get(
                    "review_status"
                )
                or "NOT_REVIEWED",
                "retained_document_records": sum(
                    d["source_id"] == live_sources.get(s["source_code"], {}).get("id")
                    for d in retained_docs
                ),
            }
            for s in sources
        ],
        "documents": {
            "retained_records": len(retained_docs),
            "distinct_sha256": len({d["checksum_sha256"] for d in retained_docs}),
            "reviewed_distinct_sha256": next(
                t["count"]
                for t in tables[0]
                if t["metric"] == "Distinct retained reviewed docs"
            ),
        },
        "evaluation": functions,
        "protocol": protocols,
        "input_hashes": files,
        "protocol_hashes": {
            name: sha(ROOT / "research/evaluation" / name)
            for name in (
                "retrieval_tasks.md",
                "questionnaire.md",
                "stage5b_protocol.md",
            )
        },
        "exporter": "scripts/export_asset_evidence_tables.py",
        "exporter_sha256": sha(ROOT / "scripts/export_asset_evidence_tables.py"),
    }
    # Fail closed if a locator accidentally contains a machine-specific path.
    raw = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if any(
        value in raw
        for value in (
            "/Users/",
            "/Volumes/",
            "storage_key",
            "reviewer_name",
            "reviewer_receipt",
        )
    ):
        raise ValueError("Private metadata detected in public summary")
    public.parent.mkdir(parents=True, exist_ok=True)
    public.write_text(raw)
    manifest = {
        "captured_at": snapshot["captured_at"],
        "database_fingerprint": snapshot["database_fingerprint"],
        "public_summary_sha256": sha(public),
        "snapshot_sha256": sha(snapshot_path),
        "api_readback_sha256": sha(api_path),
        "inputs": files,
        "methodology": payload["methodology"],
        "totals": {
            "assets": len(asset_rows),
            "primary": sum(a["scope"] == "primary" for a in asset_rows),
            "components": sum(a["scope"] == "component" for a in asset_rows),
            "l2": sum(a["technical_l2"] for a in asset_rows),
            "sources": len(sources),
            "expected_file": sum(s["file_expected"] == "true" for s in sources),
        },
        "browser_acceptance": "NOT_RETESTED",
    }
    (output / "coverage-readback-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(json.dumps(manifest["totals"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--api-readback", type=Path, required=True)
    parser.add_argument(
        "--controlled-dir", type=Path, default=ROOT / "research/dataset/reviewed"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--public", type=Path, default=ROOT / "apps/web/src/data/methodology.json"
    )
    args = parser.parse_args()
    export(
        args.snapshot, args.api_readback, args.controlled_dir, args.output, args.public
    )
