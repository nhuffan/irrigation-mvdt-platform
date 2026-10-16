"""Offline B02 compiler: explicit reviewed facts only, with retained provenance."""

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid5

from scripts.prepare_empirical_scope import boolean, read_rows
from scripts.prepare_reviewed_asset_batch import indexed, signed, split
from scripts.research_common import digest, research_code, write_csv

TYPES = {
    "technical": "TECHNICAL",
    "conditions": "CONDITION",
    "inspections": "INSPECTION",
    "repairs": "REPAIR",
    "maintenance": "MAINTENANCE",
}
OTHER = {"MONITORING", "MODEL_OUTPUT", "REFERENCE"}
STATUSES = {"EXTRACTED", "REVIEW_PENDING", "VERIFIED", "REJECTED", "NOT_APPLICABLE"}
FIELDS = {
    "conditions": {
        "condition_status",
        "summary",
        "defect_description",
        "recommended_action",
    },
    "inspections": {
        "inspection_type",
        "inspector",
        "summary",
        "observation",
        "condition_status",
        "recommended_action",
    },
    "repairs": {
        "repair_type",
        "problem_description",
        "repair_description",
        "result",
        "responsible_unit",
    },
    "maintenance": {"maintenance_type", "description", "result", "responsible_unit"},
}
DATE_FIELDS = {
    "conditions": "condition_date",
    "inspections": "inspection_date",
    "repairs": "repair_date",
    "maintenance": "maintenance_date",
}
PLACEHOLDERS = {"n/a", "na", "no data", "unknown", "-", "null"}


def meaningful(value, row):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing source value")
    if (
        value.strip().lower() in PLACEHOLDERS
        and not row.get("literal_value_reason", "").strip()
    ):
        raise ValueError("Placeholder is not a fact; literal text requires rationale")
    return value


def locator(value):
    # Reject broad file-only citations while allowing page/table, sheet-cell and named sections.
    patterns = [
        r"PDF:p[1-9][0-9]*(?::.+)?",
        r"DRAWING:sheet-[^:]+:.+",
        r"XLSX:[^!]+![A-Z]+[1-9][0-9]*(?::[A-Z]+[1-9][0-9]*)?",
        r'DOCX:section\s+"[^"\n]+"',
    ]
    if not any(re.fullmatch(p, value or "") for p in patterns):
        raise ValueError(
            "Exact PDF page/drawing note/sheet-cell/named section locator required"
        )


def compile_batch(
    candidates, attributes, evidence, sources, targets, id_rows, kind, reviewer
):
    if kind not in TYPES or not reviewer.strip():
        raise ValueError("Known batch type and reviewer required")
    indexed(candidates, "candidate_id")
    emap = indexed(evidence, "evidence_id")
    smap = indexed(sources, "source_code")
    tmap = indexed(targets, "target_asset_code")
    ids, used = {}, set()
    for r in id_rows:
        key = (r["record_type"], r["code"])
        uid = str(UUID(r["uuid"]))
        if key in ids or uid in used or not research_code(r["code"]):
            raise ValueError("Invalid/duplicate reserved UUID map")
        ids[key] = uid
        used.add(uid)
    dictionary = {}
    for r in attributes:
        key = (r["category_code"], r["attribute_key"])
        if (
            key in dictionary
            or not research_code(key[0])
            or not re.fullmatch(r"[a-z][a-z0-9_]*", key[1])
        ):
            raise ValueError("Invalid/duplicate controlled attribute")
        boolean(r["required_by_maim"])
        if not r.get("attribute_label"):
            raise ValueError("Controlled attribute label required")
        dictionary[key] = r
    for row in candidates:
        if (
            row.get("record_type") not in set(TYPES.values()) | OTHER
            or row.get("candidate_status") not in STATUSES
        ):
            raise ValueError(
                "Unknown candidate type/status; migrate legacy candidate columns explicitly"
            )
    selected = [
        r
        for r in candidates
        if r["record_type"] == TYPES[kind] and r["candidate_status"] == "VERIFIED"
    ]
    report = {
        "status": "NO_VERIFIED_CANDIDATES",
        "candidate_count": len(candidates),
        "verified_candidate_count": sum(
            r["candidate_status"] == "VERIFIED" for r in candidates
        ),
        "rejected_candidate_count": sum(
            r["candidate_status"] == "REJECTED" for r in candidates
        ),
        "selected_count": len(selected),
        "imported_count": 0,
        "unchanged_count": 0,
        "monitoring_not_imported_count": sum(
            r["record_type"] == "MONITORING" for r in candidates
        ),
        "model_output_not_imported_count": sum(
            r["record_type"] == "MODEL_OUTPUT" for r in candidates
        ),
        "missing_required_fields": [],
        "unresolved_conflicts": [],
        "asset_counts": dict(Counter(r["asset_code"] for r in selected)),
        "source_counts": dict(Counter(r["source_code"] for r in selected)),
    }
    if not selected:
        return None, [], report
    records, provenance, errors = [], [], []
    for row in selected:
        cid = row["candidate_id"]
        try:
            asset, source = row["asset_code"], row["source_code"]
            if (
                not research_code(asset)
                or not research_code(source)
                or asset not in tmap
                or source not in smap
            ):
                raise ValueError(
                    "Candidate must reference RS target/source inventories"
                )
            target = tmap[asset]
            if (
                not boolean(target["in_scope"])
                or target["verification_status"] != "VERIFIED"
            ):
                raise ValueError("Target identity/inclusion not approved")
            if (
                asset not in split(smap[source]["related_asset_codes"])
                or smap[source]["verification_status"] == "REJECTED"
            ):
                raise ValueError("Source rejected or unrelated to asset")
            e = emap.get(row["evidence_id"])
            if (
                not e
                or e["source_code"] != source
                or asset not in split(e["asset_codes"])
            ):
                raise ValueError("Evidence/source/asset linkage mismatch")
            public_url = urlsplit(e.get("source_url", ""))
            public_file = (
                public_url.scheme == "https"
                and bool(public_url.hostname)
                and not public_url.username
                and not public_url.password
                and bool(re.fullmatch(r"[0-9a-f]{64}", e.get("checksum_sha256", "")))
                and bool(e.get("file_name", "").strip())
            )
            if e["mime_type"] == "application/vnd.google-apps.folder" or not (
                e.get("drive_file_id") or public_file
            ):
                raise ValueError("Exact physical evidence file required")
            if e["review_status"] not in {"REVIEWED", "VERIFIED"}:
                raise ValueError("Evidence is not reviewed")
            signed(e)
            signed(row)
            locator(row["source_locator"])
            aid, sid = ids[("assets", asset)], ids[("data_sources", source)]
            # Identity excludes value/source to ensure a corrected candidate reuses its ID.
            uid = str(uuid5(UUID(aid), "B02:" + kind + ":" + cid))
            record = {
                "id": uid,
                "asset_id": aid,
                "source_id": sid,
                "verification_status": "VERIFIED",
            }
            if kind == "technical":
                rule = dictionary.get((target["category"], row["candidate_field"]))
                if not rule or row["candidate_unit"] != rule["expected_unit"]:
                    raise ValueError("Controlled key and exact unit match required")
                if row["candidate_label"] != rule["attribute_label"]:
                    raise ValueError(
                        "Candidate label differs from controlled dictionary"
                    )
                value = meaningful(row["candidate_value"], row)
                value_type = row.get("candidate_value_type")
                if value_type not in {"number", "text"}:
                    raise ValueError(
                        "Declare candidate_value_type number or text; no inference"
                    )
                numeric = float(value) if value_type == "number" else None
                if numeric is not None and not math.isfinite(numeric):
                    raise ValueError("Numeric values must be finite")
                record.update(
                    attribute_key=rule["attribute_key"],
                    attribute_label=rule["attribute_label"],
                    value_number=numeric,
                    value_text=value if value_type == "text" else None,
                    unit=rule["expected_unit"] or None,
                )
            else:
                # Optional explicit review columns preserve partial-date semantics.
                # Legacy reviewed batches retain their existing full-date contract.
                if (
                    "temporal_precision" in row
                    and row["temporal_precision"] != "FULL_DATE"
                ):
                    raise ValueError(
                        "Partial/unknown temporal precision cannot become a full event date"
                    )
                if (
                    "completion_status" in row
                    and row["completion_status"] != "VERIFIED"
                ):
                    raise ValueError(
                        "Listed/planned work is not verified completed O&M"
                    )
                if (
                    "source_eligibility" in row
                    and row["source_eligibility"] != "VERIFIED_EVENT"
                ):
                    raise ValueError(
                        "Reference-only source cannot establish an operational event"
                    )
                if "mapping_verified" in row and row["mapping_verified"] != "true":
                    raise ValueError("Candidate asset mapping is not verified")
                raw_date = row.get("candidate_date", "")
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
                    raise ValueError(
                        "Full event date required; do not invent partial dates"
                    )
                event_date = date.fromisoformat(raw_date).isoformat()
                payload = json.loads(row.get("record_payload") or "{}")
                if not isinstance(payload, dict) or set(payload) - FIELDS[kind]:
                    raise ValueError("Event payload has unknown/system fields")
                for v in payload.values():
                    if v is not None:
                        meaningful(v, row)
                required = {
                    "conditions": "condition_status",
                    "repairs": "repair_description",
                    "maintenance": "description",
                }.get(kind)
                if required and not payload.get(required):
                    raise ValueError(f"Required event field: {required}")
                if kind == "inspections" and not any(
                    payload.get(k) for k in ["summary", "observation"]
                ):
                    raise ValueError(
                        "Inspection needs explicit source-supported summary/observation"
                    )
                if not row.get("event_basis", "").strip():
                    raise ValueError(
                        "Event basis must explain documented event, not monitoring/model inference"
                    )
                record.update(payload)
                record[DATE_FIELDS[kind]] = event_date
            records.append(record)
            provenance.append(
                {
                    "record_type": kind,
                    "record_id": uid,
                    "candidate_id": cid,
                    "asset_code": asset,
                    "source_code": source,
                    "evidence_id": e["evidence_id"],
                    "drive_file_id": e.get("drive_file_id", ""),
                    "source_url": e.get("source_url", ""),
                    "checksum_sha256": e.get("checksum_sha256", ""),
                    "source_locator": row["source_locator"],
                    "reviewer": row["reviewer"],
                    "reviewed_at": row["reviewed_at"],
                    "candidate_sha256": digest(row),
                }
            )
        except (ValueError, KeyError, TypeError) as error:
            errors.append({"candidate_id": cid, "reason": str(error)})
    if errors:
        report.update(status="NOT_READY", missing_required_fields=errors)
        return None, [], report
    if kind == "technical":
        groups = defaultdict(list)
        for record in records:
            groups[(record["asset_id"], record["attribute_key"])].append(record)
        report["unresolved_conflicts"] = [
            {
                "asset_id": aid,
                "attribute_key": key,
                "record_ids": [r["id"] for r in group],
                "status": "UNREVIEWED",
            }
            for (aid, key), group in groups.items()
            if len({(r["value_number"], r["value_text"], r["unit"]) for r in group}) > 1
        ]
    batch = {
        "import_batch": "B02-" + kind.upper(),
        "data_origin": "RESEARCH",
        "reviewed_by": reviewer,
        "source_reference": "Reviewed B02 candidates; exact file/locator mapping in provenance.csv and review_manifest.json",
        "records": {kind: records},
    }
    report["status"] = "READY_TO_IMPORT"
    return batch, provenance, report


def main():
    parser = argparse.ArgumentParser()
    for key in (
        "candidates",
        "attributes",
        "evidence",
        "sources",
        "targets",
        "id-map",
        "output",
    ):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--batch-type", required=True, choices=TYPES)
    parser.add_argument("--reviewed-by", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError(
            "Output already exists; reuse saved batch/UUIDs, never overwrite audit evidence"
        )
    names = ["candidates", "attributes", "evidence", "sources", "targets", "id_map"]
    hashes = {
        k: hashlib.sha256(getattr(args, k).read_bytes()).hexdigest() for k in names
    }
    inputs = {k: read_rows(getattr(args, k)) for k in names}
    try:
        batch, provenance, report = compile_batch(
            *inputs.values(), args.batch_type, args.reviewed_by
        )
    except (ValueError, KeyError, TypeError) as error:
        batch, provenance = None, []
        report = {"status": "NOT_READY", "blockers": [str(error)]}
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {"inputs": inputs, "input_sha256": hashes, "provenance": provenance}
    if batch:
        batch["review_manifest_sha256"] = digest(manifest)
        report["batch_sha256"] = digest(batch)
        (args.output / ("B02-" + args.batch_type + ".json")).write_text(
            json.dumps(batch, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        )
        (args.output / "review_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        )
        write_csv(
            args.output / "id_map.csv",
            [
                {
                    "record_type": p["record_type"],
                    "candidate_id": p["candidate_id"],
                    "uuid": p["record_id"],
                }
                for p in provenance
            ],
            ["record_type", "candidate_id", "uuid"],
        )
        write_csv(args.output / "provenance.csv", provenance, list(provenance[0]))
    for name, data in [
        ("input_sha256.json", hashes),
        ("verification_report.json", report),
    ]:
        (args.output / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        )
    print(json.dumps(report, indent=2))
    if not batch:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
