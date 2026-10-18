"""Read-only public completion extension; approval inputs and raw evidence stay private.

Counts of observed records are descriptive. Draft MAIM observations never become
approved completeness denominators merely because technical records exist.
"""

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict

SCHEMA = "METHODOLOGY-COMPLETION-v1"
DASHBOARD_SCHEMA = "METHODOLOGY-DASHBOARD-v2"
PUBLIC_REPO = "https://github.com/nhuffan/irrigation-mvdt-platform/blob/main/"
RECORD_KINDS = ("technical", "conditions", "inspections", "repairs", "maintenance")
AUTHORITY = {
    "AUTHORITATIVE",
    "SUPPORTING",
    "REFERENCE",
    "UNKNOWN_AUTHORITY",
    "NOT_ELIGIBLE",
}
ROLES = {
    "RESEARCHER",
    "DOMAIN_EXPERT",
    "CUSTODIAN",
    "INDEPENDENT_REVIEWER",
    "AI_METHOD_REVIEWER",
}
GROUPS = {"OTHER_METHODOLOGY", "DOMAIN_APPROVAL", "F02_F05_EVIDENCE"}
STATUSES = {
    "IMPLEMENTED": "Implemented software or measured record availability; not research validation.",
    "SOURCE_REPORTED": "Information reported by retained source evidence; no present-day certification.",
    "HISTORICAL_TEST": "Recorded test result on its original date and dataset; not a fresh browser test.",
    "PROTOCOL_ONLY": "Method is documented; completion or outcome is not established.",
    "NOT_COLLECTED": "No empirical observations or scores have been collected for this publication.",
    "PENDING_REVIEW": "Applicability, approval or evidence remains unresolved; unknown is not zero.",
    "NOT_APPLICABLE": "An explicitly reviewed scope exclusion; unavailable data alone does not justify N/A.",
}
DOCS = [
    (
        "protocol",
        "Evaluation protocol",
        "research/evaluation/protocol.md",
        "PROTOCOL_ONLY",
    ),
    (
        "stage5b",
        "Stage 5B empirical protocol",
        "research/evaluation/stage5b_protocol.md",
        "PROTOCOL_ONLY",
    ),
    (
        "retrieval",
        "Retrieval tasks and success criteria",
        "research/evaluation/retrieval_tasks.md",
        "PROTOCOL_ONLY",
    ),
    (
        "questionnaire",
        "Custom eight-item questionnaire (not SUS)",
        "research/evaluation/questionnaire.md",
        "NOT_COLLECTED",
    ),
    (
        "results",
        "Results and discussion evidence map",
        "research/evaluation/results_outline.md",
        "PROTOCOL_ONLY",
    ),
    (
        "closure",
        "Role-scoped methodology closure",
        "research/evaluation/methodology_closure_review.md",
        "PENDING_REVIEW",
    ),
    (
        "checkpoints",
        "Methodology checkpoints",
        "research/evaluation/methodology_checkpoint_review.md",
        "PENDING_REVIEW",
    ),
    (
        "exporter",
        "Read-only methodology exporter",
        "scripts/export_methodology_dashboard.py",
        "IMPLEMENTED",
    ),
    (
        "completion",
        "Completion calculations",
        "scripts/methodology_completion.py",
        "IMPLEMENTED",
    ),
]


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def read_rows(path):
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def pick(row, keys):
    return {key: row.get(key) for key in keys}


def nonmissing(row):
    return row.get("value_number") is not None or bool(
        (row.get("value_text") or "").strip()
    )


def public_json(payload):
    """Fail closed; do not silently publish unsafe metadata or scrub evidence values."""
    raw = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    forbidden = r"/Users/|/Volumes/|/private/|/home/|[A-Za-z]:\\\\|storage_key|reviewer_name|reviewer_receipt|(?:[?&](?:key|token|access_token|api_key)=)|-----BEGIN .*PRIVATE KEY"
    if re.search(forbidden, raw, re.IGNORECASE):
        raise ValueError("Private metadata detected in public summary")
    return raw


def require_v1_compatible(payload, previous):
    """Same export retains every original v1 property/value, except schema version."""

    def check(now, old, path=""):
        if isinstance(old, dict):
            if not isinstance(now, dict):
                raise TypeError(f"Backward compatibility mismatch: {path}")
            for key, value in old.items():
                if path == "" and key == "schema_version":
                    continue
                if key not in now:
                    raise ValueError(f"Backward compatibility missing: {path}/{key}")
                check(now[key], value, f"{path}/{key}")
        elif isinstance(old, list):
            if not isinstance(now, list) or len(now) != len(old):
                raise ValueError(f"Backward compatibility list mismatch: {path}")
            for index, value in enumerate(old):
                check(now[index], value, f"{path}/{index}")
        elif now != old:
            raise ValueError(f"Backward compatibility value mismatch: {path}")

    check(payload, previous)


def live_readback(api, models, sources=()):
    assets = {}
    for code, data in sorted(api.items()):
        asset = data["asset"]
        location = asset.get("location") or {}
        condition = data.get("current-condition")
        assets[code] = {
            "id": asset["id"],
            "name": asset.get("name"),
            "parent_asset_id": asset.get("parent_asset_id"),
            "category_code": asset["category"]["code"],
            "category_name": asset["category"].get("name"),
            "technical_labels": sorted(
                [
                    {
                        "id": technical["id"],
                        "key": technical["attribute_key"],
                        "label": technical.get("attribute_label"),
                        "source_id": technical.get("source_id"),
                        "nested_source_id": (technical.get("source") or {}).get("id"),
                    }
                    for technical in data["technical"]
                ],
                key=lambda item: item["id"],
            ),
            "geometry": asset.get("geometry"),
            "location": pick(
                location,
                (
                    "location_status",
                    "review_state",
                    "evidence_id",
                    "crs",
                    "geometry",
                    "reviewed_at",
                ),
            ),
            "documents": sorted(
                [
                    pick(
                        d,
                        (
                            "id",
                            "source_id",
                            "checksum_sha256",
                            "original_file_name",
                            "mime_type",
                            "file_size",
                            "page_count",
                        ),
                    )
                    for d in data["documents"]
                ],
                key=lambda d: d["id"],
            ),
            "links": sorted(
                [
                    pick(
                        link,
                        (
                            "id",
                            "model_id",
                            "asset_id",
                            "object_key",
                            "verification_status",
                        ),
                    )
                    for link in data["model-links"]
                ],
                key=lambda d: d["id"],
            ),
            "events": sorted(
                [
                    pick(
                        event,
                        (
                            "record_id",
                            "event_type",
                            "event_date",
                            "asset_id",
                            "source_id",
                            "verification_status",
                        ),
                    )
                    for event in data["timeline"]
                    if event["verification_status"] == "VERIFIED"
                ],
                key=lambda d: d["record_id"],
            ),
            "condition": pick(
                condition, ("id", "asset_id", "source_id", "verification_status")
            )
            if condition
            else None,
        }
    model_keys = (
        "id",
        "source_id",
        "model_code",
        "name",
        "format",
        "coordinate_mode",
        "longitude",
        "latitude",
        "height",
        "heading",
        "pitch",
        "roll",
        "scale",
        "verification_status",
    )
    return {
        "assets": assets,
        "models": sorted(
            [pick(model, model_keys) for model in models], key=lambda d: d["id"]
        ),
        "sources": sorted(
            [
                pick(
                    source,
                    (
                        "id",
                        "source_code",
                        "title",
                        "source_type",
                        "source_date",
                        "authority_level",
                        "verification_status",
                    ),
                )
                for source in sources
            ],
            key=lambda d: d["id"],
        ),
    }


def observed_field(field, key, unit, data, scoped_records, source_ids):
    asset = data["asset"]
    if field == "identity":
        available = bool(asset.get("id") and asset.get("asset_code"))
    elif field == "category":
        available = bool(asset.get("category", {}).get("code"))
    elif field == "spatial":
        available = asset.get("geometry") is not None
    elif field == "source":
        available = any(r.get("source_id") in source_ids for r in scoped_records)
    elif field == "technical":
        if not key:
            return "UNKNOWN"
        available = any(
            r.get("attribute_key") == key
            and (r.get("unit") or "") == (unit or "")
            and r.get("verification_status") == "VERIFIED"
            and nonmissing(r)
            for r in data["technical"]
        )
    elif field == "condition":
        available = bool(
            data.get("current-condition")
            and data["current-condition"].get("verification_status") == "VERIFIED"
        )
    elif field in {"inspection", "maintenance", "repair"}:
        available = any(
            e["event_type"] == field.upper() and e["verification_status"] != "REJECTED"
            for e in data["timeline"]
        )
    elif field == "document":
        available = bool(data["documents"])
    elif field == "three_d":
        # A LOCAL representative is not an identity-verified building or geographic placement.
        return "UNKNOWN" if data["model-links"] else "MISSING"
    else:
        return "UNKNOWN"
    return "AVAILABLE" if available else "MISSING"


def maim_rows(payload, api, base, controlled, scoped_records, source_ids):
    requirements = read_rows(controlled / "maim_requirements.csv")
    reviews = read_rows(controlled / "maim_review.csv")
    dictionary = read_rows(controlled / "technical_attribute_dictionary.csv")
    required_approval = "PENDING_REVIEW"
    # Domain approvals must be bound to the current package, not a historical receipt.
    declaration = json.loads((controlled / "methodology_review.json").read_text())
    approved = any(
        a.get("approval_type") == "DOMAIN_REVIEW"
        and a.get("scope") == "MAIM"
        and a.get("reviewer_role") == "DOMAIN_EXPERT"
        and a.get("decision") == "APPROVED"
        and a.get("package_fingerprint") == payload["methodology"]["fingerprint"]
        for a in declaration.get("approval", {}).get("entries", [])
    )
    if approved:
        # Reuse role/fingerprint validation; a malformed or stale declaration cannot
        # establish an approved denominator, even if it says APPROVED.
        from scripts.methodology_review import validate_role_approvals

        approved = not validate_role_approvals(
            declaration.get("approval", {}), payload["methodology"]["fingerprint"]
        )
    if approved:
        required_approval = "APPROVED"
    rows = []
    for asset in payload["assets"]:
        code, data = asset["asset_code"], api[asset["asset_code"]]
        category = data["asset"]["category"]["code"]
        rules = [r for r in reviews if r["asset_code"] == code]
        fields = []
        for rule in rules:
            field, key = rule["field"], rule.get("attribute_key", "")
            match = next(
                (
                    r
                    for r in requirements
                    if r["category"] == category
                    and r["field"] == field
                    and r.get("attribute_key", "") == key
                ),
                {},
            )
            disposition = rule.get("disposition")
            requirement = (
                "NOT_APPLICABLE"
                if disposition == "NOT_APPLICABLE"
                else "REQUIRED"
                if rule.get("effective_required") == "true"
                else "OPTIONAL"
            )
            fields.append(
                {
                    "field": field,
                    "attribute_key": key,
                    "expected_unit": match.get("expected_unit") or None,
                    "requirement": requirement,
                    "review_status": "APPROVED" if approved else "PENDING_REVIEW",
                    "observed": observed_field(
                        field,
                        key,
                        match.get("expected_unit"),
                        data,
                        scoped_records.get(code, []),
                        source_ids,
                    ),
                    "basis": "Controlled MAIM proposal; canonical geometry only; technical rules require exact key/unit; parent technical values remain on components.",
                }
            )
        proposed = None
        if fields:
            applicable = [f for f in fields if f["requirement"] == "REQUIRED"]
            proposed = {
                "applicable": len(applicable),
                "available": sum(f["observed"] == "AVAILABLE" for f in applicable),
                "missing": sum(f["observed"] == "MISSING" for f in applicable),
                "unknown": sum(f["observed"] == "UNKNOWN" for f in applicable),
                "not_applicable": sum(
                    f["requirement"] == "NOT_APPLICABLE" for f in fields
                ),
                "optional": sum(f["requirement"] == "OPTIONAL" for f in fields),
            }
        final = proposed if approved and proposed else {}
        rows.append(
            {
                "asset_id": asset["asset_id"],
                "asset_code": code,
                "scope": asset["scope"],
                "parent_asset_code": asset["parent_asset_code"],
                "category": category,
                "status": "SOURCE_REPORTED"
                if approved and proposed
                else "PENDING_REVIEW",
                **{
                    k: final.get(k)
                    for k in (
                        "applicable",
                        "available",
                        "missing",
                        "not_applicable",
                        "unknown",
                    )
                },
                "proposed": proposed,
                "fields": fields,
            }
        )
    return {
        "status": "SOURCE_REPORTED" if approved else "PENDING_REVIEW",
        "approval_status": required_approval,
        "dictionary": {
            "defined_entries": len(dictionary),
            "required_entries": sum(
                row.get("required_by_maim") == "true" for row in dictionary
            ),
            "status": "PENDING_REVIEW",
            "limitation": "A dictionary documents known keys/units; optional entries do not establish required applicability, especially for parents or newly admitted components.",
        },
        "basis": "Primary category/per-asset proposals in controlled maim_requirements.csv + maim_review.csv; component admission does not approve component MAIM. Technical dictionary values are optional and do not define the denominator.",
        "rows": rows,
    }


def public_readiness(payload, controlled):
    gates = read_rows(controlled / "readiness_gates.csv")
    resolution = {
        r["gate_id"]: r for r in read_rows(controlled / "mc_r_gate_resolution.csv")
    }
    public = []
    for gate in gates:
        ident = gate["gate_id"]
        if not re.fullmatch(r"[A-Za-z0-9_]+", ident):
            raise ValueError("Invalid public gate identifier")
        resolved = resolution.get(ident, {})
        status = (
            gate.get("current_status")
            if gate.get("current_status")
            in {"PASS", "FAIL", "PENDING", "N/A", "NOT_TESTED"}
            else "PENDING"
        )
        group = resolved.get("blocker_group")
        if group not in GROUPS:
            group = (
                "F02_F05_EVIDENCE"
                if ident in {"F02", "F05", "CASE_geometry"}
                else "DOMAIN_APPROVAL"
                if "maim" in ident.lower()
                else "OTHER_METHODOLOGY"
            )
        owner = resolved.get("decision_owner")
        public.append(
            {
                "id": ident,
                "label": ident.replace("_", " "),
                "category": gate.get("category")
                if re.fullmatch(r"[A-Z_]+", gate.get("category", ""))
                else "METHODOLOGY",
                "required": gate.get("required_for_freeze") == "true",
                "status": status,
                "decision_owner": owner
                if owner in ROLES | {"PENDING_EVIDENCE"}
                else "UNASSIGNED",
                "blocker_group": group,
            }
        )
    pending = [
        g for g in public if g["required"] and g["status"] not in {"PASS", "N/A"}
    ]
    groups = [
        {
            "id": group,
            "unresolved_gate_count": len(
                [g for g in pending if g["blocker_group"] == group]
            ),
            "gate_ids": [g["id"] for g in pending if g["blocker_group"] == group],
        }
        for group in sorted({g["blocker_group"] for g in pending})
    ]
    return {
        "status": payload["methodology"]["status"],
        "dataset_status": payload["methodology"]["dataset_status"],
        "compiler_blocker_count": payload["methodology"]["unresolved_gate_count"],
        "declared_gates": public,
        "groups": groups,
        "accepted_gate_ids": [g["id"] for g in public if g["status"] == "PASS"],
        "unresolved_gate_ids": [g["id"] for g in pending],
        "not_applicable_gate_ids": [g["id"] for g in public if g["status"] == "N/A"],
        "approval_summary": [
            {
                "approval_type": kind,
                "scope": scope,
                "required_role": role,
                "status": "PENDING_REVIEW",
            }
            for kind, scope, role in [
                ("RESEARCHER_APPROVAL", "METHODOLOGY_PACKAGE", "RESEARCHER"),
                ("DOMAIN_REVIEW", "MAIM", "DOMAIN_EXPERT"),
            ]
        ],
        "limitation": "Declared gate decisions and groups are not fresh approval. Compiler blockers include additional consistency checks and do not equal unresolved declared-gate rows. Raw review receipts, names, signatures and gate free text are private.",
    }


def build_completion(
    payload,
    snapshot,
    api,
    base,
    sources,
    controlled,
    root,
    previous=None,
    compiler_report=None,
):
    rows = snapshot["rows"]
    assets = {a["asset_code"]: a for a in payload["assets"]}
    ids = {a["asset_id"] for a in assets.values()}
    sources_by_code = {r["source_code"]: r for r in rows["data_sources"]}
    source_ids = {
        sources_by_code[s["source_code"]]["id"]
        for s in sources
        if s["source_code"] in sources_by_code
    }
    reviews = {r["source_code"]: r for r in read_rows(controlled / "source_review.csv")}
    scoped = {
        kind: [r for r in rows[kind] if r["asset_id"] in ids] for kind in RECORD_KINDS
    }
    all_records = [r for records in scoped.values() for r in records]
    by_asset = {
        code: [r for r in all_records if r["asset_id"] == a["asset_id"]]
        for code, a in assets.items()
    }
    # Mirror the web-visible model set, not only an old allowlist. An additional
    # visible model must invalidate live alignment rather than disappear from it.
    managed_reservoir = payload.get("reservoir_id") or next(
        iter(base.get("reservoir_ids", [])), None
    )
    models = [
        m
        for m in rows["models"]
        if m.get("reservoir_id") == managed_reservoir
        and m.get("model_code", "").startswith("RS-")
    ]

    # A model source is a direct source for its linked parent, never a transfer
    # of child-building technical properties into the complex.
    model_by_id = {m["id"]: m for m in models}
    for code, data in api.items():
        by_asset[code] += [
            model_by_id[link["model_id"]]
            for link in data["model-links"]
            if link["model_id"] in model_by_id
        ]
    documents = [d for d in rows["documents"] if d["source_id"] in source_ids]
    retained = [
        d
        for d in documents
        if d.get("checksum_sha256")
        and snapshot["storage_sha256"].get(d["storage_key"]) == d["checksum_sha256"]
    ]
    retained_sources = {d["source_id"] for d in retained}
    expected = [s for s in sources if s["file_expected"] == "true"]
    known_dates = [
        {
            "code": s["source_code"],
            "source_date": sources_by_code.get(s["source_code"], {}).get("source_date")
            or s.get("source_date")
            or None,
        }
        for s in sources
    ]
    date_fields = (
        "document_date",
        "issue_date",
        "revision_date",
        "event_date",
        "coverage_start",
        "coverage_end",
    )
    for row in known_dates:
        row["date_status"] = "SOURCE_REPORTED" if row["source_date"] else "UNKNOWN"
        for field in date_fields:
            value = reviews.get(row["code"], {}).get(field, "")
            row[field] = (
                value if re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", value) else None
            )
    technical = scoped["technical"]
    provenance = [t for a in payload["assets"] for t in a["technical_readback"]]
    groups = defaultdict(list)
    for record in technical:
        if nonmissing(record):
            groups[(record["asset_id"], record["attribute_key"])].append(record)
    code_by_id = {a["asset_id"]: code for code, a in assets.items()}
    conflicts = [
        {
            "asset_code": code_by_id[asset_id],
            "attribute_key": key,
            "record_ids": sorted(r["id"] for r in values),
            "status": "UNRESOLVED",
        }
        for (asset_id, key), values in sorted(groups.items())
        if len(
            {
                json.dumps(
                    [r.get("value_number"), r.get("value_text"), r.get("unit")],
                    sort_keys=True,
                )
                for r in values
            }
        )
        > 1
    ]
    captured = payload["captured_at"]
    metrics = []

    def metric(
        ident,
        label,
        n,
        d,
        scope,
        formula,
        basis,
        limitation="",
        unit="ratio",
        status="IMPLEMENTED",
    ):
        metrics.append(
            {
                "id": ident,
                "label": label,
                "numerator": n,
                "denominator": d,
                "value": n / d
                if d and n is not None
                else n
                if unit == "count"
                else None,
                "formula": formula,
                "unit": unit,
                "scope": scope,
                "status": status,
                "captured_at": captured,
                "basis": basis,
                "limitation": limitation
                or "Descriptive availability; not survey, current-condition or methodology approval.",
            }
        )

    primary = [a for a in assets.values() if a["scope"] == "primary"]
    metric(
        "primary_registry",
        "Registered primary targets",
        len(primary),
        len(
            [
                t
                for t in read_rows(controlled / "target_assets.csv")
                if t["in_scope"] == "true"
            ]
        ),
        "Primary sample",
        "registered in-scope primary IDs / controlled in-scope primary targets",
        ["target_assets.csv", "API assets"],
    )
    metric(
        "controlled_registered_sources",
        "Registered controlled sources",
        len(source_ids),
        len(sources),
        "Controlled logical source inventory",
        "registered controlled source IDs / controlled source entries",
        ["source_inventory.csv", "DB data_sources"],
    )
    metric(
        "expected_sources_retained",
        "Expected-file sources with matching retained bytes",
        sum(
            sources_by_code.get(s["source_code"], {}).get("id") in retained_sources
            for s in expected
        ),
        len(expected),
        "Expected-file sources only",
        "expected-file source IDs with >=1 checksum-matching retained file / expected-file sources",
        ["source_inventory.csv", "DB documents", "storage SHA-256"],
        "A source-level measure; distinct PDFs, metadata records and asset-document edges are separate units.",
    )
    metric(
        "document_integrity",
        "Retained metadata with matching bytes",
        len(retained),
        len(documents),
        "Controlled-source document metadata",
        "metadata rows with retained bytes matching recorded SHA-256 / scoped document metadata",
        ["DB documents", "storage SHA-256"],
    )
    metric(
        "distinct_reviewed_pdfs",
        "Distinct retained reviewed PDFs",
        payload["documents"]["reviewed_distinct_sha256"],
        None,
        "IMPORT-reviewed retained files deduplicated by SHA-256",
        "count(unique retained reviewed PDF SHA-256)",
        ["document_review.csv", "storage SHA-256"],
        unit="count",
    )
    metric(
        "asset_document_edges",
        "Asset-document edges",
        sum(a["linked_document_records"] for a in assets.values()),
        None,
        "10 asset rows; shared source-derived documents count once per linked asset",
        "sum(asset linked document metadata rows)",
        ["Table 4", "API asset documents"],
        "Not a count of distinct files or an expansion of the source denominator.",
        unit="count",
    )
    metric(
        "source_review_coverage",
        "Sources with formal authority-review row",
        sum(s["source_code"] in reviews for s in sources),
        len(sources),
        "Controlled sources",
        "sources with source_review row / controlled sources",
        ["source_review.csv"],
        "Review-row presence is not authority verification.",
    )
    metric(
        "source_dates_known",
        "Sources with a reported date",
        sum(r["source_date"] is not None for r in known_dates),
        len(sources),
        "Controlled sources",
        "sources with nonblank source_date / controlled sources",
        ["source_inventory.csv", "DB data_sources"],
        "A source date is neither event date nor confirmation of currentness.",
    )
    metric(
        "source_review_dates_known",
        "Sources with a date in formal source review",
        sum(any(row[field] for field in date_fields) for row in known_dates),
        len(sources),
        "Controlled sources; source-review document/issue/revision/event/coverage dates",
        "sources with >=1 explicitly reported source-review date / controlled sources",
        ["source_review.csv"],
        "Separate from source_date, review approval timestamp, event admission and currentness.",
    )
    metric(
        "technical_traceability",
        "L2 fields with source and exact locator",
        sum(
            t["source_id"] in source_ids
            and bool(t["source_code"] and (t["locator"] or "").strip())
            for t in provenance
        ),
        len(provenance),
        "Direct technical records across 4 primary + 6 components",
        "L2 record IDs with included source and nonblank locator / L2 record IDs",
        ["API technical reviewed_provenance"],
        "Each record counted once; no parent/child joins. L2 does not promote UNKNOWN source authority.",
    )
    metric(
        "verified_record_ratio",
        "Verified scoped technical/O&M records",
        sum(r["verification_status"] == "VERIFIED" for r in all_records),
        len(all_records),
        "Scoped technical + condition/inspection/repair/maintenance records",
        "VERIFIED record IDs / all scoped record IDs",
        ["DB scoped records"],
        "Describes stored verification labels; does not create current-condition or operational approval.",
    )
    metric(
        "technical_conflict_rate",
        "Exact asset/key value conflicts",
        len(conflicts),
        len(groups),
        "Nonmissing technical asset/key groups",
        "groups with >1 distinct value/text/unit tuple / asset-key groups with a nonmissing value",
        ["DB scoped technical"],
        "No unit conversion or semantic equivalence inferred; separate historical keys are not collapsed. No conflict is auto-resolved.",
    )
    metric(
        "canonical_primary_geometry",
        "Primary canonical geometry presence",
        sum(a["canonical_geometry_present"] for a in primary),
        len(primary),
        "4 primary targets",
        "primary assets with stored canonical geometry / primary targets",
        ["DB assets"],
        "Reference-only points excluded. Presence is not positional validation; F02 unchanged.",
    )
    metric(
        "verified_primary_om",
        "Primary assets with verified O&M",
        sum(a["verified_om_records"] > 0 for a in primary),
        len(primary),
        "4 primary targets",
        "primary assets with >=1 VERIFIED O&M record / primary targets",
        ["DB scoped O&M"],
        "Zero records remain absent; do not substitute Good or operational readiness.",
    )
    metric(
        "reference_points",
        "Reviewed reference locations",
        sum(a["reference_locations"] for a in assets.values()),
        len(assets),
        "4 primary + 6 components",
        "assets with reference-location metadata / registered scoped assets",
        ["API asset location"],
        "Navigation references; not canonical geometry or F02 validation.",
    )
    metric(
        "approved_maim",
        "Approved MAIM completeness",
        None,
        None,
        "Per-asset approved applicability (not yet available)",
        "available approved required fields / approved applicable fields",
        ["maim_requirements.csv", "maim_review.csv", "methodology_review.json"],
        "No approved final denominator; draft proposals and component data remain separate.",
        status="PENDING_REVIEW",
    )
    counts = lambda values: [
        {"classification": k, "count": v} for k, v in sorted(Counter(values).items())
    ]
    authority = [
        reviews.get(s["source_code"], {}).get("authority_class", "UNKNOWN_AUTHORITY")
        for s in sources
    ]
    authority = [a if a in AUTHORITY else "UNKNOWN_AUTHORITY" for a in authority]
    metric(
        "source_authority_unknown",
        "Sources with unknown authority",
        authority.count("UNKNOWN_AUTHORITY"),
        len(sources),
        "Controlled sources",
        "UNKNOWN_AUTHORITY or absent formal authority-review row / controlled source entries",
        ["source_review.csv"],
        "Absent review remains unknown; admitted fields do not upgrade source authority.",
    )
    docs = [
        {
            "id": ident,
            "label": label,
            # Local implementation bytes are hashed here but have not been published.
            # Only existing unchanged protocol/review documents have public links.
            "href": PUBLIC_REPO + path if path.startswith("research/") else None,
            "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest(),
            "status": status,
        }
        for ident, label, path, status in DOCS
        if (root / path).is_file()
    ]
    workflow = [
        {
            "id": ident,
            "label": label,
            "status": status,
            "evidence": evidence,
            "limitation": note,
        }
        for ident, label, status, evidence, note in [
            (
                "input",
                "Controlled input and retained-byte audit",
                "IMPLEMENTED",
                ["exporter"],
                "Source entries, physical PDFs and metadata edges have separate denominators.",
            ),
            (
                "review",
                "Source, identity and field review",
                "SOURCE_REPORTED",
                ["closure"],
                "Scoped L2 admissions do not close missing authority, MAIM or case-study approvals.",
            ),
            (
                "registry",
                "Primary/component registry",
                "IMPLEMENTED",
                ["stage5b"],
                "4 primary research units plus 6 separately reported components.",
            ),
            (
                "integration",
                "GIS, 3D, documents and O&M integration",
                "IMPLEMENTED",
                ["protocol"],
                "F02/F05 lack evidence; reference points and LOCAL representative model do not close either.",
            ),
            (
                "retrieval",
                "Paired retrieval and questionnaire study",
                "NOT_COLLECTED",
                ["retrieval", "questionnaire"],
                "No human participant, time, task-success or questionnaire result is asserted.",
            ),
            (
                "evaluation",
                "Functional and data evaluation",
                "HISTORICAL_TEST",
                ["protocol", "results"],
                "F01-F21 keep their original dates/scopes; software/API checks are not browser or research validation.",
            ),
            (
                "readiness",
                "Methodology approval and dataset freeze",
                "PENDING_REVIEW",
                ["closure", "checkpoints"],
                "NOT_READY / NOT_FROZEN; current package-bound role approvals remain required.",
            ),
        ]
    ]
    workflow.insert(
        2,
        {
            "id": "maim",
            "label": "Identity and MAIM applicability",
            "status": "PENDING_REVIEW",
            "evidence": ["stage5b", "closure"],
            "limitation": "Stable inventory does not approve required field applicability; primary proposals/domain review remain pending, and components lack dedicated reviewed MAIM.",
        },
    )
    criteria = [
        "Correct record ID/date, or correct absence if confirmed by the source-backed answer key.",
        "Correct VERIFIED condition/status/date or explicit absence; never substitute an unverified condition.",
        "Correct maintenance source and document ID/file, or identify that the file is unavailable.",
        "Complete scoped repair-record set without unrelated assets.",
        "Correct Asset ID and geometry checked against reviewed spatial evidence.",
        "Correct model/object key and resolved Asset ID, or correctly identify no mapping.",
    ]
    feasibility = [
        "ABSENCE_ONLY",
        "ABSENCE_ONLY",
        "BLOCKED_NO_MAINTENANCE_RECORD",
        "ABSENCE_ONLY",
        "BLOCKED_F02",
        "REPRESENTATIVE_ONLY",
    ]
    notes = [
        "No verified research inspection exists; absence answer requires reviewed answer key.",
        "No verified current condition exists; absence cannot become Good.",
        "No scoped maintenance record exists to support a positive record-to-document task.",
        "No scoped repair history exists; empty-set task requires reviewed answer key.",
        "Two reference points support navigation only; canonical geometry and F02 remain missing.",
        "One MGMT parent-representative LOCAL object; no child-building identity or surveyed placement.",
    ]
    retrieval = [
        {
            "id": task["id"],
            "prompt": task["prompt"],
            "success_criterion": criterion,
            "feasibility": feasible,
            "status": "PROTOCOL_ONLY",
            "basis": ["retrieval_tasks.md", note],
        }
        for task, criterion, feasible, note in zip(
            payload["protocol"]["tasks"], criteria, feasibility, notes
        )
    ]
    previous_fp = (previous or {}).get("methodology", {}).get("fingerprint")
    completion = {
        "schema_version": SCHEMA,
        "captured_at": captured,
        "status_definitions": [
            {"status": k, "definition": v} for k, v in STATUSES.items()
        ],
        "study_design": {
            "title": "Dau Tieng headworks case study",
            "design": "Bounded single-case prototype and evidence-integration study; planned paired retrieval evaluation",
            "status": "PROTOCOL_ONLY",
            "primary_denominator": len(primary),
            "component_count": len(assets) - len(primary),
            "scope_rationale": "The four approved primary asset IDs remain the research sample. Three intake sluices and three management buildings are components, reported separately; their L2 fields are not reassigned to the parent or added to the primary denominator.",
            "units": [
                {"unit": unit, "definition": definition, "scope": scope}
                for unit, definition, scope in [
                    (
                        "primary asset",
                        "Independent controlled research sample unit",
                        "4 primary targets",
                    ),
                    (
                        "component",
                        "Separately identified child, not another primary sample",
                        "6 components",
                    ),
                    (
                        "field",
                        "Direct technical record with exact key/value/unit and L2 provenance",
                        f"{len(provenance)} observed direct L2 records",
                    ),
                    (
                        "source",
                        "Logical controlled inventory entry",
                        f"{len(sources)} entries; {len(source_ids)} registered DB sources",
                    ),
                    (
                        "document",
                        "Retained metadata record or distinct SHA-256; edges counted separately",
                        "Scoped source-linked PDFs",
                    ),
                    (
                        "event",
                        "Dated condition/inspection/repair/maintenance record",
                        "No verified research event",
                    ),
                    (
                        "model",
                        "Model resource and object-to-asset link",
                        "LOCAL representative context, not geographic/building certification",
                    ),
                ]
            ],
            "collection_method": [
                "Inspect existing controlled source inventory and retained files; retain exact-byte SHA-256 and locator.",
                "Use approved primary/component inventory and read-only DB/API readback; do not discover new evidence in this stage.",
            ],
            "admission_method": [
                "Separate candidate extraction, source/identity/field review and explicit scope allowlist.",
                "Check exact original bytes, field value/unit/locator, duplicate/conflict and asset mapping before audit, dry-run, apply, retry and API verification.",
                "Store accepted fields as SOURCE_REPORTED / HISTORICAL_DOCUMENTED at L2; no inferred current condition, geometry, source-authority or methodology approval.",
            ],
        },
        "maim": maim_rows(payload, api, base, controlled, by_asset, source_ids),
        "metrics": metrics,
        "source_quality": {
            "authority": counts(authority),
            "verification": counts(
                sources_by_code.get(s["source_code"], {}).get(
                    "verification_status", "NOT_ADMITTED"
                )
                for s in sources
            ),
            "review": counts(
                reviews.get(s["source_code"], {}).get("review_status") or "NOT_REVIEWED"
                for s in sources
            ),
            "dates": known_dates,
            "conflicts": conflicts,
        },
        "workflow": workflow,
        "retrieval_tasks": retrieval,
        "baseline_protocol": {
            "design": "Within-participant paired BASELINE / MVDT on identical frozen information",
            "status": "NOT_COLLECTED",
            "pairing_keys": [
                "dataset_version",
                "task_version",
                "participant_group",
                "participant_id",
                "task_id",
            ],
            "timing": "Start at task reveal; stop at submitted answer. Timezone-aware start/end must match positive elapsed seconds within one second; failed attempts retain actual time, never zero-imputed.",
            "timeout": "Predeclare timeout per task and source-backed answer key before sessions; no universal timeout value has been approved.",
            "order_and_training": "Counterbalance workflow order with assignment ledger and equivalent variants; equal training and unscored practice; record device/network/interruptions/assistance.",
            "analysis": "Pair same task/version/cohort/participant; time reduction only when both succeed and baseline time > 0. Report all-attempt success and exclusions separately; keep DOMAIN_STAFF separate from RESEARCH_TEAM benchmarks.",
            "bias": "Successful-only timing selection, convenience sampling, small sample, training/order/memorization and hardware/network effects prevent unsupported causal or generalized claims.",
            "participant_count": None,
            "observations": None,
            "time_results": None,
        },
        "questionnaire": {
            "instrument": "CUSTOM_8_ITEM_NOT_SUS",
            "status": "NOT_COLLECTED",
            "item_count": len(payload["protocol"]["questionnaire"]),
            "scale": "1 Strongly disagree to 5 Strongly agree; NA/blank remain missing",
            "analysis": "Per-item actual n, mean, median, range and sample SD only when n>=2; no SUS transformation, validated total scale or invented themes/quotes.",
            "results": None,
        },
        "readiness": public_readiness(payload, controlled),
        "live_readback": live_readback(
            api, models, [s for s in rows["data_sources"] if s["id"] in source_ids]
        ),
        "provenance": {
            "methodology_package_fingerprint": payload["methodology"]["fingerprint"],
            "previous_package_fingerprint": previous_fp,
            "package_status": "BASELINE_UNAVAILABLE"
            if not previous_fp
            else "UNCHANGED"
            if previous_fp == payload["methodology"]["fingerprint"]
            else "CHANGED",
            "completion_artifact_sha256": None,
            "documents": docs,
        },
    }
    from methodology_quantitative import build_quantitative

    completion["quantitative"] = build_quantitative(
        payload, completion, snapshot, api, base, controlled, root, compiler_report
    )
    completion["provenance"]["completion_artifact_sha256"] = digest(completion)
    public_json(completion)
    return completion


def write_completion_artifacts(completion, output):
    """Ignored audit artifacts contain the same sanitized content as the public summary."""
    output.mkdir(parents=True, exist_ok=True)
    if "quantitative" in completion:
        from methodology_quantitative import write_quantitative_artifacts

        write_quantitative_artifacts(completion["quantitative"], output)
    (output / "metrics-manifest.json").write_text(
        public_json(
            {
                "schema_version": SCHEMA,
                "captured_at": completion["captured_at"],
                "metrics": completion["metrics"],
                "provenance": completion["provenance"],
            }
        )
    )
    matrix = []
    for section, basis, status, gap in [
        (
            "Study design and units",
            "protocol/stage5b + approved inventory",
            "PROTOCOL_ONLY",
            "Formal case-study package approval pending",
        ),
        (
            "MAIM applicability",
            "controlled MAIM proposal/review + API observations",
            "PENDING_REVIEW",
            "Primary draft rules not domain-approved; no component-specific MAIM approval",
        ),
        (
            "Quality and provenance",
            "DB/API + retained byte checks + source review",
            "IMPLEMENTED",
            "Source authority/date unknowns remain visible",
        ),
        (
            "Workflow and functional criteria",
            "F01-F21 controlled original dates and repo protocols",
            "HISTORICAL_TEST",
            "F02/F05 evidence pending; no fresh browser acceptance",
        ),
        (
            "Retrieval and questionnaire",
            "T1-T6, paired design, custom8 not SUS",
            "NOT_COLLECTED",
            "No participants/times/scores; positive O&M/GIS tasks blocked",
        ),
        (
            "Readiness and reproducibility",
            "compiler + role-scoped gates + fingerprints",
            "PENDING_REVIEW",
            "NOT_READY/NOT_FROZEN; no approval rebound",
        ),
        (
            "Asset field and source/file drilldown (MC-3)",
            "10 scoped API asset pages; 44 direct L2 value/unit/source/locator readbacks; source inventory versus retained PDF versus document edges",
            "IMPLEMENTED",
            "Human MAIM/identity and O&M/spatial evidence remain pending; representative LOCAL 3D is not building/geometry verification; follow-up 3D panel browser measurement remains pending",
        ),
        (
            "Compatibility, drift and replay safeguards (MC-4)",
            "Retained v1 fields; exact technical and completion readbacks; schema/privacy tests and deterministic exporter inputs",
            "IMPLEMENTED",
            "Software guards do not supply missing domain approvals or participant results; browser/3D acceptance and the final stage test/replay evidence are reported separately",
        ),
    ]:
        matrix.append(
            {
                "content": section,
                "previous": "PARTIAL",
                "exported": "YES",
                "basis": basis,
                "status": status,
                "remaining_gap": gap,
            }
        )
    with (output / "content-matrix.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(matrix[0]))
        writer.writeheader()
        writer.writerows(matrix)
