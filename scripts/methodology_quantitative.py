"""Optional quantitative evidence extension: observed availability is not approved completeness.

Only retained inputs are read. Candidate registers contribute aggregate classifications,
never candidate values, identities, raw text, receipts or admitted research records.
"""

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date

SCHEMA = "METHODOLOGY-QUANTITATIVE-v1"
KINDS = ("technical", "conditions", "inspections", "repairs", "maintenance")
REGISTER_SPECS = (
    (
        "technical_candidates",
        "Legacy technical candidate register",
        "b02_candidate_records.csv",
        "candidate_status",
    ),
    (
        "candidate_conflicts",
        "Retained candidate conflict register",
        "b02_conflict_review.csv",
        "status",
    ),
    (
        "maintenance_candidates",
        "Maintenance workbook candidate decisions",
        "maintenance_2021_2025_review.csv",
        "import_decision",
    ),
    (
        "maintenance_mapping",
        "Maintenance candidate identity decisions",
        "maintenance_asset_mapping_review.csv",
        "decision",
    ),
    (
        "geometry_review",
        "Primary spatial evidence decisions",
        "geometry_review.csv",
        "geometry_status",
    ),
    (
        "model_mapping",
        "Legacy model mapping decisions",
        "model_asset_mapping_review.csv",
        "mapping_status",
    ),
    (
        "document_review",
        "Retained document review decisions",
        "document_review.csv",
        "document_status",
    ),
    (
        "source_file_review",
        "Declared source file representations",
        "source_review.csv",
        "digital_file_status",
    ),
    (
        "maim_closure",
        "MAIM closure classifications",
        "maim_closure_review.csv",
        "classification",
    ),
)
PUBLIC_STATUSES = {
    "NOT_APPLICABLE",
    "VERIFIED",
    "UNVERIFIED",
    "PENDING",
    "REVIEW_PENDING",
    "KEEP_OUTSIDE_DB",
    "REFERENCE_ONLY",
    "AMBIGUOUS_ASSET",
    "ACCEPT_CANDIDATE",
    "OUT_OF_SCOPE",
    "NOT_AVAILABLE",
    "AMBIGUOUS",
    "IMPORT",
    "FILE_PRESENT",
    "FILE_MISSING",
    "MULTIPLE_REPRESENTATIONS",
    "UNRESOLVED",
    "COHERENT",
    "NEEDS_EVIDENCE",
    "NEEDS_DOMAIN_CONFIRMATION",
    "RESOLVED",
    "RETAIN_BOTH",
    "REJECTED",
}
QUALITY_COUNTS = (
    "total_fields",
    "numeric_fields",
    "text_fields",
    "both_value_fields",
    "missing_value_fields",
    "unit_present",
    "unit_missing",
    "unit_text",
    "locator_present",
    "locator_missing",
    "source_linked",
    "source_missing",
)


def rows(path):
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def counts(values, key="value"):
    return [
        {key: value, "count": count} for value, count in sorted(Counter(values).items())
    ]


def meaningful(record):
    return record.get("value_number") is not None or bool(
        (record.get("value_text") or "").strip()
    )


def result(ident, n, d, status="OBSERVED"):
    return {
        "metric_id": ident,
        "numerator": n,
        "denominator": d,
        "value": n / d if n is not None and d else None,
        "status": status if d else "NO_DENOMINATOR" if status == "OBSERVED" else status,
    }


def dictionary():
    """Keep protocol variants named, including their original eligibility rules."""
    definitions = [
        (
            "observed_direct_technical",
            "Observed direct technical presence",
            "Descriptive registered-inventory availability, not formal completeness.",
            "Registered scoped assets with >=1 direct VERIFIED nonmissing technical record",
            "Registered assets in the explicitly named primary/component/all group",
            "Zero is a value; parent complex direct zero is not a failed child requirement.",
            "No asset/category N/A is inferred; per-parent denominator remains null when child evidence is separately reported.",
            "Snapshot technical values are historical/source-reported, not current condition.",
            "Descriptive inventory scope only; components never enlarge the four-primary paper sample.",
            ["protocol", "stage5b"],
        ),
        (
            "protocol_5a_technical",
            "Protocol 5A technical coverage",
            "Legacy protocol presence rule, retained separately from Stage5B required-key coverage.",
            "Included VERIFIED assets with >=1 VERIFIED nonmissing technical record",
            "Included VERIFIED assets",
            "Numeric zero counts; blank/null values do not; REGISTERED is not VERIFIED.",
            "Empty VERIFIED denominator gives null; no component/sample expansion.",
            "Frozen scoped records and their verification at evaluation time.",
            "STAGE-5A / protocol.md; unresolved approval cannot become an evaluated result.",
            ["protocol"],
        ),
        (
            "protocol_5b_technical",
            "Protocol 5B required technical coverage",
            "All approved required keys and exact units must be satisfied.",
            "Approved technically eligible targets with every required VERIFIED key/value/unit",
            "Approved targets eligible for technical MAIM, excluding reviewed N/A",
            "No defined/reviewed required-key set means PENDING_REVIEW, not zero or 100%.",
            "Only reviewed N/A removes a field/eligible target; components need their own approved rules.",
            "Approved dataset as-of and frozen record scope; historical fields do not certify today.",
            "STAGE-5B-v1; formal denominator remains unresolved.",
            ["stage5b"],
        ),
        (
            "source_traceability",
            "Source traceability",
            "Record IDs linked to included sources without expanded joins.",
            "Scoped technical/O&M records linked to a controlled source ID",
            "All scoped technical/O&M record IDs",
            "Missing source remains in denominator; source-ID availability is not authority.",
            "No source/record removed merely for missing provenance.",
            "Captured DB/API; no currentness implied.",
            "Direct records only, counted once per named group.",
            ["protocol", "stage5b"],
        ),
        (
            "verified_source_records",
            "Verified-source records",
            "Source verification differs from record verification.",
            "Source-linked technical/O&M records whose source is VERIFIED",
            "All source-linked scoped technical/O&M records",
            "Unknown/UNVERIFIED source does not count as VERIFIED even when its L2 field is VERIFIED.",
            "No source-linked records gives null.",
            "Captured source verification labels, not independent domain attestation.",
            "Direct scoped record IDs, not source count or joined-document edges.",
            ["protocol"],
        ),
        (
            "verified_record_ratio",
            "Verified record ratio",
            "Availability of stored VERIFIED record labels.",
            "VERIFIED scoped technical/O&M record IDs",
            "All scoped technical/O&M record IDs",
            "Nonverified rows stay in denominator; missing endpoints are UNAVAILABLE, not zero.",
            "No scoped records gives null.",
            "Record status in captured readback; L2 is source-reported/historical.",
            "Direct scoped record IDs.",
            ["protocol"],
        ),
        (
            "document_coverage",
            "Expected-source document coverage",
            "Expected logical sources with checksum-matching retained bytes.",
            "Expected-file sources with >=1 accessible retained checksum-matching file",
            "Explicit controlled expected-file source list",
            "Missing file/source stays in denominator; metadata alone does not establish bytes.",
            "Only explicit reviewed file expectation changes denominator.",
            "Captured storage integrity; not a source/event date.",
            "Source grain; distinct files and asset-document edges remain separate.",
            ["protocol", "stage5b"],
        ),
        (
            "document_integrity",
            "Document integrity",
            "Retained bytes match recorded SHA-256.",
            "Scoped document metadata with matching retained bytes and checksum",
            "All scoped document metadata",
            "Missing bytes/hash never count as matches.",
            "No scoped metadata gives null.",
            "Captured storage hash, not continuous live byte verification.",
            "Metadata rows; unique SHA-256 is reported separately.",
            ["protocol"],
        ),
        (
            "observed_canonical_geometry",
            "Observed canonical geometry presence",
            "Stored geometry presence, not survey accuracy or F02.",
            "Scoped registered assets with nonnull canonical geometry",
            "Registered assets in the named group",
            "Reference locations and registry center do not satisfy canonical geometry.",
            "No asset is excluded because spatial evidence is absent.",
            "Captured API canonical geometry; no survey certification.",
            "Descriptive primary/component scope; formal GIS approval remains pending.",
            ["protocol", "stage5b"],
        ),
        (
            "observed_reference_locations",
            "Reviewed reference-location presence",
            "Navigation/presentation references, separate from canonical GIS.",
            "Scoped assets with available reviewed REFERENCE_LOCATION metadata",
            "Registered assets in the named group",
            "NO_LOCATION remains absent; no inferred asset coordinates.",
            "Reference-only is not N/A or F02 PASS.",
            "Captured reviewed location metadata.",
            "Descriptive registered-asset grain.",
            ["protocol"],
        ),
        (
            "observed_current_condition",
            "Latest verified current condition availability",
            "Only latest VERIFIED condition may be current condition.",
            "Scoped assets whose current-condition API returns VERIFIED",
            "Registered assets in the named group",
            "Absent current condition never becomes Good; technical L2 is not condition.",
            "No missing condition is automatically N/A.",
            "Latest eligible VERIFIED condition by its event date; absent remains absent.",
            "Descriptive availability; formal primary MAIM condition coverage is not inferred.",
            ["protocol", "stage5b"],
        ),
        (
            "observed_inspection",
            "Observed non-rejected inspection presence",
            "History presence, not task completion or verification quality.",
            "Scoped assets with a non-REJECTED inspection record",
            "Registered assets in the named group",
            "Missing history stays absent; no candidate register is imported.",
            "No automatic N/A; formal eligible MAIM denominator remains separate.",
            "Captured event history; dated legacy record is not today's condition.",
            "Descriptive registered inventory.",
            ["stage5b"],
        ),
        (
            "observed_maintenance",
            "Observed non-rejected maintenance presence",
            "History presence, not completed work or task success.",
            "Scoped assets with a non-REJECTED maintenance record",
            "Registered assets in the named group",
            "Candidate/workbook activities do not become admitted events.",
            "No automatic N/A; formal eligible MAIM denominator remains separate.",
            "Captured event history; planned/annual text is not a dated completed event.",
            "Descriptive registered inventory.",
            ["stage5b"],
        ),
        (
            "observed_repair",
            "Observed non-rejected repair presence",
            "Descriptive repair-history availability.",
            "Scoped assets with a non-REJECTED repair record",
            "Registered assets in the named group",
            "Empty history is absent, not evidence no repair occurred.",
            "Formal repair coverage needs reviewed eligibility; raw record count remains descriptive.",
            "Captured event history.",
            "Descriptive registered inventory.",
            ["stage5b"],
        ),
        (
            "protocol_5a_om",
            "Protocol 5A history presence",
            "Legacy presence-only history rule accepts any scoped verification state.",
            "Included VERIFIED assets with >=1 scoped history record of the selected kind",
            "Included VERIFIED assets",
            "Retain verification separately; any scoped record presence is not VERIFIED O&M.",
            "No verified-asset denominator gives null; do not pool with 5B.",
            "Frozen scoped record history, no current-condition inference.",
            "Legacy protocol.md scope.",
            ["protocol"],
        ),
        (
            "protocol_5b_om",
            "Protocol 5B eligible history coverage",
            "Non-rejected histories over approved eligible MAIM targets.",
            "Eligible approved targets with non-REJECTED selected-kind history",
            "Targets requiring that MAIM field after reviewed N/A",
            "No approved applicability means null/PENDING_REVIEW.",
            "Reviewed field-specific N/A only; missing evidence does not justify exclusion.",
            "Approved frozen event scope/date.",
            "STAGE-5B-v1, primary/component denominators reviewed separately.",
            ["stage5b"],
        ),
        (
            "observed_representative_model",
            "Representative model-link presence",
            "A retained LOCAL representative link is an implementation association.",
            "Scoped assets with a non-REJECTED link to an available visible research model",
            "Registered assets in the named group",
            "No child mapping is inferred from its parent's representative model.",
            "No missing mapping automatically becomes N/A.",
            "Captured model/link status; LOCAL is not surveyed placement or specific building identity.",
            "Descriptive association; not formal 3D completeness.",
            ["protocol", "stage5b"],
        ),
        (
            "mapping_verification",
            "Stored mapping verification ratio",
            "VERIFIED link labels among scoped links, not surveyed identity.",
            "VERIFIED scoped model-asset links",
            "All scoped research model-asset links",
            "Missing model resolution is reported separately; VERIFIED link alone is not geographic accuracy.",
            "No links gives null.",
            "Captured link verification status.",
            "Link grain; not all-asset coverage.",
            ["protocol"],
        ),
        (
            "exact_conflict_rate",
            "Exact technical conflict rate",
            "Distinct value/text/unit tuples within the same asset/key.",
            "Asset/key groups with >1 distinct nonmissing tuple",
            "Asset/key groups with >=1 nonmissing value",
            "Missing values excluded from tuple comparison, numeric zero retained; no unit conversion.",
            "No known-value groups gives null.",
            "Temporal/key differences are not silently collapsed; no expert resolution inferred.",
            "Admitted technical records only; retained register decisions remain separate.",
            ["protocol", "stage5b"],
        ),
        (
            "source_date_known",
            "Known source-date ratio",
            "Canonical source-date metadata availability.",
            "Controlled sources with a known source_date",
            "Controlled sources",
            "Review/upload/partial document dates cannot replace unknown source_date.",
            "Unknown is missing metadata, not a zero-year age.",
            "Canonical source_date only.",
            "Logical source grain.",
            ["protocol"],
        ),
        (
            "source_age",
            "Source age at approved dataset date",
            "Age requires both a precise source date and approved dataset as-of.",
            "Approved as-of date minus exact canonical source_date (days)",
            "Sources with valid exact dates and an approved as-of (descriptive distribution)",
            "Any missing/partial/future date or unapproved as-of yields unavailable age.",
            "Never substitute snapshot/API/upload date for dataset as-of.",
            "SOURCE_DATE_TO_APPROVED_AS_OF; current missing as-of remains PENDING_REVIEW.",
            "Source metadata age is not current condition or authority.",
            ["protocol", "stage5b"],
        ),
        (
            "maim_completeness",
            "Approved applicable MAIM completeness",
            "Approved field-level presence and verification rules.",
            "Satisfied approved applicable MAIM fields per asset",
            "Approved applicable fields after documented N/A",
            "Unknown dictionary/applicability is null; direct parent zero does not erase component evidence.",
            "Written scope rationale and appropriate review required; components do not inherit primary proposals.",
            "Approved frozen scope; current package remains NOT_READY/NOT_FROZEN.",
            "Per-asset with primary/component aggregates separate; no fabricated denominator.",
            ["stage5b", "closure"],
        ),
    ]
    keys = (
        "id",
        "name",
        "definition",
        "numerator_rule",
        "denominator_rule",
        "missing_rule",
        "na_rule",
        "temporal_basis",
        "scope_policy",
        "basis_docs",
    )
    entries = [dict(zip(keys, values)) for values in definitions]
    references = {
        "document_coverage": "completion.metrics.expected_sources_retained",
        "document_integrity": "completion.metrics.document_integrity",
        "source_date_known": "completion.metrics.source_dates_known",
        "source_age": "completion.quantitative.source_ages",
        "maim_completeness": "completion.quantitative.coverage.assets.maim",
    }
    for entry in entries:
        entry["result_reference"] = references.get(
            entry["id"], "completion.quantitative.coverage.groups.metrics"
        )
    return entries


def quality(technical, source_by_id, source_review):
    stats = dict.fromkeys(QUALITY_COUNTS, 0)
    stats["total_fields"] = len(technical)
    for row in technical:
        numeric, text = (
            row.get("value_number") is not None,
            bool((row.get("value_text") or "").strip()),
        )
        unit = row.get("unit")
        pro = row.get("reviewed_provenance") or {}
        stats["numeric_fields"] += numeric
        stats["text_fields"] += text
        stats["both_value_fields"] += numeric and text
        stats["missing_value_fields"] += not numeric and not text
        stats["unit_present"] += bool(unit and unit.strip())
        stats["unit_missing"] += not bool(unit and unit.strip())
        stats["unit_text"] += unit == "text"
        stats["locator_present"] += bool((pro.get("source_locator") or "").strip())
        stats["locator_missing"] += not bool((pro.get("source_locator") or "").strip())
        stats["source_linked"] += row.get("source_id") in source_by_id
        stats["source_missing"] += row.get("source_id") not in source_by_id
    return stats


def register_aggregates(controlled):
    result_rows = []
    for ident, label, filename, status_field in REGISTER_SPECS:
        path = controlled / filename
        register = rows(path)
        status_counts = counts(
            (
                r.get(status_field)
                if r.get(status_field) in PUBLIC_STATUSES
                else "OTHER_OR_UNCLASSIFIED"
                for r in register
            ),
            "status",
        )
        result_rows.append(
            {
                "id": ident,
                "label": label,
                "basis_file": filename,
                "entry_count": len(register) if path.is_file() else None,
                "status_counts": status_counts,
                "limitation": "Retained register classifications only; entries may be historical, overlapping or already reviewed. ACCEPT_CANDIDATE/VERIFIED in this register does not import an event or change admitted totals. Unknown labels are grouped without publishing raw text.",
            }
        )
    return result_rows


def compiler_groups(report):
    if report is None:
        return [
            {"id": ident, "finding_count": None, "status": "UNAVAILABLE"}
            for ident in ("EVIDENCE", "DOMAIN_REVIEW", "FUNCTIONAL", "PROTOCOL")
        ]
    groups = Counter()
    for finding in report.get("blockers", []):
        # Exactly one category per actual compiler finding; descriptions remain private.
        text = str(finding).lower()
        ident = (
            "FUNCTIONAL"
            if any(
                t in text
                for t in ("browser acceptance", "functional acceptance", "f02", "f05")
            )
            else "DOMAIN_REVIEW"
            if any(t in text for t in ("maim", "domain_review", "domain approval"))
            else "EVIDENCE"
            if any(
                t in text
                for t in (
                    "source",
                    "evidence",
                    "geometry",
                    "provenance",
                    "checksum",
                    "integrity",
                    "hash",
                )
            )
            else "PROTOCOL"
        )
        groups[ident] += 1
    return [
        {"id": ident, "finding_count": groups[ident], "status": report["status"]}
        for ident in ("EVIDENCE", "DOMAIN_REVIEW", "FUNCTIONAL", "PROTOCOL")
    ]


def empirical_metrics():
    return [
        {
            "id": "all_attempt_success",
            "name": "All-attempt task success",
            "formula": "successful scored attempts / all scored attempts",
            "numerator_rule": "Source-backed answer-key success=1 attempts",
            "denominator_rule": "All valid scored attempts for the same workflow/task/version/cohort, including failure and timeout",
            "missing_rule": "No observations -> null, never 0% or 100%; invalid/missing attempts reported separately.",
            "selection_bias": "Report all-attempt success separately from successful-only timing; do not pool cohorts or versions.",
            "status": "NOT_COLLECTED",
            "results": None,
        },
        {
            "id": "matched_pair_time",
            "name": "Matched successful-pair timing",
            "formula": "paired baseline seconds and MVDT seconds",
            "numerator_rule": "Elapsed times for both-successful paired trials",
            "denominator_rule": "Same participant/task/task-version/dataset/cohort with both successful and baseline >0",
            "missing_rule": "Failures/timeouts/unmatched trials are excluded only from this timing comparison and retained in success denominators; no zero imputation.",
            "selection_bias": "Successful-only selection, order/training/memorization, convenience sampling and device/network effects.",
            "status": "NOT_COLLECTED",
            "results": None,
        },
        {
            "id": "paired_time_reduction",
            "name": "Paired relative time reduction",
            "formula": "100 × (baseline_seconds − MVDT_seconds) / baseline_seconds for each eligible pair",
            "numerator_rule": "Baseline minus MVDT elapsed seconds for an eligible matched successful pair",
            "denominator_rule": "Strictly positive baseline seconds for that same pair",
            "missing_rule": "No eligible matched pairs -> null; negative reductions retained; no API-latency substitute.",
            "selection_bias": "Descriptive paired results do not establish causality or general operator improvement; disclose exclusions and actual n.",
            "status": "NOT_COLLECTED",
            "results": None,
        },
    ]


def build_quantitative(
    payload, completion, snapshot, api, base, controlled, root, compiler_report=None
):
    db = snapshot["rows"]
    assets = payload["assets"]
    for asset in assets:
        data = api.get(asset["asset_code"])
        if not data or any(
            not isinstance(data.get(key), list)
            for key in ("technical", "documents", "timeline", "model-links")
        ):
            raise ValueError(
                "Quantitative API readback unavailable; do not substitute zero"
            )
    inventories = rows(controlled / "source_inventory.csv")
    source_codes = {s["source_code"] for s in inventories}
    source_by_id = {
        s["id"]: s for s in db["data_sources"] if s["source_code"] in source_codes
    }
    source_review = {
        s["source_code"]: s for s in rows(controlled / "source_review.csv")
    }
    maim = {a["asset_code"]: a for a in completion["maim"]["rows"]}
    records = {
        a["asset_id"]: [
            r for kind in KINDS for r in db[kind] if r["asset_id"] == a["asset_id"]
        ]
        for a in assets
    }

    def descendants(code):
        children = [a for a in assets if a["parent_asset_code"] == code]
        return children + [
            v for child in children for v in descendants(child["asset_code"])
        ]

    models_by_id = {m["id"]: m for m in completion["live_readback"]["models"]}
    model_ids = set(models_by_id)

    def asset_metrics(chosen):
        chosen_records = [r for a in chosen for r in records[a["asset_id"]]]
        source_linked = [
            r for r in chosen_records if r.get("source_id") in source_by_id
        ]
        items = [
            result(
                "observed_direct_technical",
                sum(
                    any(
                        t["verification_status"] == "VERIFIED" and meaningful(t)
                        for t in api[a["asset_code"]]["technical"]
                    )
                    for a in chosen
                ),
                len(chosen),
            ),
            result("source_traceability", len(source_linked), len(chosen_records)),
            result(
                "verified_source_records",
                sum(
                    source_by_id[r["source_id"]]["verification_status"] == "VERIFIED"
                    for r in source_linked
                ),
                len(source_linked),
            ),
            result(
                "verified_record_ratio",
                sum(r["verification_status"] == "VERIFIED" for r in chosen_records),
                len(chosen_records),
            ),
            result(
                "observed_canonical_geometry",
                sum(
                    api[a["asset_code"]]["asset"].get("geometry") is not None
                    for a in chosen
                ),
                len(chosen),
            ),
            result(
                "observed_reference_locations",
                sum(
                    (api[a["asset_code"]]["asset"].get("location") or {}).get(
                        "location_status"
                    )
                    == "REFERENCE_LOCATION"
                    and (api[a["asset_code"]]["asset"].get("location") or {}).get(
                        "review_state"
                    )
                    == "AVAILABLE"
                    for a in chosen
                ),
                len(chosen),
            ),
            result(
                "observed_current_condition",
                sum(
                    bool(
                        api[a["asset_code"]].get("current-condition")
                        and api[a["asset_code"]]["current-condition"].get(
                            "verification_status"
                        )
                        == "VERIFIED"
                    )
                    for a in chosen
                ),
                len(chosen),
            ),
            result(
                "observed_representative_model",
                sum(
                    any(
                        link["model_id"] in model_ids
                        and link["verification_status"] != "REJECTED"
                        for link in api[a["asset_code"]]["model-links"]
                    )
                    for a in chosen
                ),
                len(chosen),
            ),
        ]
        for field in ("inspection", "maintenance", "repair"):
            items.append(
                result(
                    "observed_" + field,
                    sum(
                        any(
                            e["event_type"] == field.upper()
                            and e["verification_status"] != "REJECTED"
                            for e in api[a["asset_code"]]["timeline"]
                        )
                        for a in chosen
                    ),
                    len(chosen),
                )
            )
        verified_assets = [
            a
            for a in chosen
            if api[a["asset_code"]]["asset"].get("data_status") == "VERIFIED"
        ]
        items.append(
            result(
                "protocol_5a_technical",
                sum(
                    any(
                        t["verification_status"] == "VERIFIED" and meaningful(t)
                        for t in api[a["asset_code"]]["technical"]
                    )
                    for a in verified_assets
                ),
                len(verified_assets),
                "PROTOCOL_ONLY",
            )
        )
        chosen_ids = {a["asset_id"] for a in chosen}
        links = [link for a in chosen for link in api[a["asset_code"]]["model-links"]]
        technical_groups = defaultdict(set)
        for technical in db["technical"]:
            if technical["asset_id"] in chosen_ids and meaningful(technical):
                technical_groups[
                    (technical["asset_id"], technical["attribute_key"])
                ].add(
                    json.dumps(
                        [
                            technical.get("value_number"),
                            technical.get("value_text"),
                            technical.get("unit"),
                        ],
                        sort_keys=True,
                    )
                )
        items += [
            result(
                "mapping_verification",
                sum(link["verification_status"] == "VERIFIED" for link in links),
                len(links),
            ),
            result(
                "exact_conflict_rate",
                sum(len(values) > 1 for values in technical_groups.values()),
                len(technical_groups),
            ),
            result("protocol_5a_om", None, None, "PROTOCOL_ONLY_KIND_SPECIFIC"),
        ]
        items += [
            result(ident, None, None, "PENDING_REVIEW")
            for ident in (
                "protocol_5b_technical",
                "protocol_5b_om",
                "maim_completeness",
            )
        ]
        return items

    coverage_assets, quality_assets, lineage, task_rows = [], [], [], []
    all_technical = []
    for asset in assets:
        code, ident = asset["asset_code"], asset["asset_id"]
        data, technical = api[code], api[code]["technical"]
        all_technical += technical
        nested_count = sum(child["technical_l2"] for child in descendants(code))
        formal = maim[code]
        proposed = formal["proposed"]
        # Verified-record-backed required fields are separate from generic presence.
        verified_fields = 0
        for field in formal["fields"]:
            if field["requirement"] != "REQUIRED":
                continue
            kind = {
                "condition": "conditions",
                "inspection": "inspections",
                "maintenance": "maintenance",
                "repair": "repairs",
                "technical": "technical",
            }.get(field["field"])
            if kind:
                candidates = [
                    r
                    for r in db[kind]
                    if r["asset_id"] == ident and r["verification_status"] == "VERIFIED"
                ]
                if kind == "technical":
                    candidates = [
                        r
                        for r in candidates
                        if field["attribute_key"]
                        and r["attribute_key"] == field["attribute_key"]
                        and (r.get("unit") or "") == (field["expected_unit"] or "")
                        and meaningful(r)
                    ]
                verified_fields += bool(candidates)
        raw_presence = []
        for field in formal["fields"]:
            if field["requirement"] != "REQUIRED":
                continue
            name, key = field["field"], field["attribute_key"]
            kind = {
                "condition": "conditions",
                "inspection": "inspections",
                "maintenance": "maintenance",
                "repair": "repairs",
                "technical": "technical",
            }.get(name)
            if name == "technical" and not key:
                raw_presence.append(None)
            elif kind:
                raw_presence.append(
                    any(
                        r["asset_id"] == ident
                        and (
                            kind != "technical"
                            or r["attribute_key"] == key
                            and meaningful(r)
                        )
                        for r in db[kind]
                    )
                )
            elif name == "identity":
                raw_presence.append(
                    bool(data["asset"].get("id") and data["asset"].get("asset_code"))
                )
            elif name == "category":
                raw_presence.append(bool(data["asset"].get("category", {}).get("code")))
            elif name == "spatial":
                raw_presence.append(data["asset"].get("geometry") is not None)
            elif name == "source":
                raw_presence.append(
                    any(r.get("source_id") in source_by_id for r in records[ident])
                    or any(
                        models_by_id.get(link["model_id"], {}).get("source_id")
                        in source_by_id
                        for link in data["model-links"]
                    )
                )
            elif name == "document":
                raw_presence.append(bool(data["documents"]))
            elif name == "three_d":
                raw_presence.append(bool(data["model-links"]))
            else:
                raw_presence.append(None)
        observed = (
            None
            if proposed is None
            else {
                "applicable": proposed["applicable"],
                "present": sum(value is True for value in raw_presence),
                "verified_record": verified_fields,
                "missing": sum(value is False for value in raw_presence),
                "not_applicable": proposed["not_applicable"],
                "unknown": sum(value is None for value in raw_presence),
                "optional": proposed["optional"],
            }
        )
        per_asset_metrics = asset_metrics([asset])
        if not technical and nested_count:
            per_asset_metrics[0] = result(
                "observed_direct_technical", 0, None, "DESCENDANTS_REPORTED_SEPARATELY"
            )
        coverage_assets.append(
            {
                "asset_id": ident,
                "asset_code": code,
                "scope": asset["scope"],
                "parent_asset_code": asset["parent_asset_code"],
                "direct_l2": asset["technical_l2"],
                "descendant_l2": nested_count,
                "maim": {
                    "status": formal["status"],
                    "applicable": formal["applicable"],
                    "present": formal["available"],
                    "verified_record": None,
                    "missing": formal["missing"],
                    "not_applicable": formal["not_applicable"],
                    "proposed": observed,
                    "proposed_semantics": "Present is raw field/record/association presence, regardless of verification; verified_record counts required fields backed by VERIFIED records with exact technical key/unit. Identity/category/source/model presence is not independent verification. A LOCAL representative link does not verify building identity. These draft observations are not MAIM completion or participant success.",
                    "proposed_not_applicable": [
                        {
                            "field": field["field"],
                            "reason": "The controlled primary 3D eligibility excludes this target; this declared scope exclusion does not certify missing geometry or grant general MAIM approval."
                            if field["field"] == "three_d"
                            else "Declared field exclusion requires its controlled scope rationale and review; it is not inferred from absent data.",
                            "basis": "maim_review.csv disposition; target_assets.csv requires_3d",
                        }
                        for field in formal["fields"]
                        if field["requirement"] == "NOT_APPLICABLE"
                    ],
                },
                "metrics": per_asset_metrics,
            }
        )
        quality_assets.append(
            {
                "asset_id": ident,
                "asset_code": code,
                "category_code": data["asset"]["category"]["code"],
                "scope": asset["scope"],
                **quality(technical, source_by_id, source_review),
            }
        )
        source_groups = defaultdict(list)
        for field in technical:
            source_groups[field.get("source_id")].append(field)
        for source_id, fields in sorted(
            source_groups.items(), key=lambda item: str(item[0])
        ):
            source = source_by_id.get(source_id)
            all_docs = [d for d in db["documents"] if d["source_id"] == source_id]
            retained = [
                d
                for d in all_docs
                if d.get("checksum_sha256")
                and snapshot["storage_sha256"].get(d["storage_key"])
                == d["checksum_sha256"]
            ]
            linked = [d for d in data["documents"] if d["source_id"] == source_id]
            lineage.append(
                {
                    "asset_id": ident,
                    "asset_code": code,
                    "source_id": source_id,
                    "source_code": source["source_code"] if source else None,
                    "field_count": len(fields),
                    "attribute_keys": sorted({f["attribute_key"] for f in fields}),
                    "locators": sorted(
                        {
                            (f.get("reviewed_provenance") or {}).get("source_locator")
                            or ""
                            for f in fields
                        }
                    ),
                    "field_locators": [
                        {
                            "attribute_key": key,
                            "locators": sorted(
                                {
                                    (f.get("reviewed_provenance") or {}).get(
                                        "source_locator"
                                    )
                                    or ""
                                    for f in fields
                                    if f["attribute_key"] == key
                                }
                            ),
                        }
                        for key in sorted({f["attribute_key"] for f in fields})
                    ],
                    "retained_document_records": len(retained),
                    "linked_document_records": len(linked),
                    "availability": "LINKED_DOCUMENT"
                    if any(d["id"] in {r["id"] for r in retained} for d in linked)
                    else "RETAINED_SOURCE_FILE_NO_ASSET_EDGE"
                    if retained
                    else "LINKED_METADATA_BYTES_UNAVAILABLE"
                    if linked
                    else "NO_UI_DOCUMENT_METADATA"
                    if source
                    else "UNKNOWN_SOURCE",
                    "asset_href": f"/assets/{ident}#technical",
                    "source_href": f"/data-sources/{source_id}/documents"
                    if source
                    else None,
                    "documents": [
                        {
                            "id": d["id"],
                            "href": f"/documents/{d['id']}",
                            "checksum_sha256": d.get("checksum_sha256"),
                        }
                        for d in sorted(retained, key=lambda row: row["id"])
                    ],
                }
            )
        for task in ("T1", "T2", "T3", "T4", "T5", "T6"):
            if task in {"T1", "T4"}:
                kind = "INSPECTION" if task == "T1" else "REPAIR"
                available = sum(
                    e["event_type"] == kind and e["verification_status"] == "VERIFIED"
                    for e in data["timeline"]
                )
                state, reason = (
                    (
                        "AVAILABLE",
                        "Verified history can be inspected; latest/set scoring still requires a reviewed answer key.",
                    )
                    if available
                    else (
                        "ABSENCE_ONLY",
                        "No verified history is present. A source-reviewed absence answer is not a completed participant task.",
                    )
                )
            elif task == "T2":
                available = int(
                    bool(
                        data.get("current-condition")
                        and data["current-condition"]["verification_status"]
                        == "VERIFIED"
                    )
                )
                state, reason = (
                    (
                        "AVAILABLE",
                        "Latest verified condition is available; task scoring is not collected.",
                    )
                    if available
                    else (
                        "ABSENCE_ONLY",
                        "No latest VERIFIED condition; technical design/history must not substitute for current condition.",
                    )
                )
            elif task == "T3":
                available = sum(
                    e["event_type"] == "MAINTENANCE"
                    and e["verification_status"] == "VERIFIED"
                    for e in data["timeline"]
                )
                state, reason = (
                    (
                        "PENDING_REVIEW",
                        "Maintenance source/document linkage needs an assigned-record answer key.",
                    )
                    if available
                    else (
                        "BLOCKED",
                        "No verified maintenance record is available for a positive supporting-document task; candidate registers are not admitted events.",
                    )
                )
            elif task == "T5":
                available = int(data["asset"].get("geometry") is not None)
                state, reason = (
                    (
                        "PENDING_REVIEW",
                        "Stored geometry needs reviewed positional evidence and an answer key; presence alone does not pass F02.",
                    )
                    if available
                    else (
                        "BLOCKED",
                        "Canonical geometry is absent. Reference-only navigation does not satisfy the original geometry-accuracy task.",
                    )
                )
            else:
                available = sum(
                    link["model_id"] in model_ids
                    and link["verification_status"] != "REJECTED"
                    for link in data["model-links"]
                )
                state, reason = (
                    (
                        "REPRESENTATIVE_ONLY",
                        "LOCAL parent-representative association is available; no specific child-building identity or survey is inferred.",
                    )
                    if available
                    else (
                        "ABSENCE_ONLY",
                        "No reviewed model binding for this asset; an absence answer needs an approved task-specific answer key.",
                    )
                )
            task_rows.append(
                {
                    "asset_id": ident,
                    "asset_code": code,
                    "scope": asset["scope"],
                    "task_id": task,
                    "evidence_status": state,
                    "available_records": available,
                    "answer_key_status": "NOT_PREPARED",
                    "reason": reason,
                    "asset_href": f"/assets/{ident}",
                }
            )
    categories = defaultdict(list)
    for a in assets:
        categories[api[a["asset_code"]]["asset"]["category"]["code"]] += api[
            a["asset_code"]
        ]["technical"]
    groups = []
    for scope in ("primary", "component", "all"):
        chosen = [a for a in assets if scope == "all" or a["scope"] == scope]
        groups.append(
            {
                "scope": scope,
                "asset_count": len(chosen),
                "direct_l2": sum(a["technical_l2"] for a in chosen),
                "descendant_l2": sum(
                    a["descendant_l2"]
                    for a in coverage_assets
                    if scope == "all" or a["scope"] == scope
                ),
                "metrics": asset_metrics(chosen),
            }
        )
    hashes = {
        "controlled--" + path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(controlled.iterdir())
        if path.is_file() and path.suffix in {".csv", ".json"}
    }
    hashes.update(
        {
            "protocol--" + name: hashlib.sha256(
                (root / "research/evaluation" / name).read_bytes()
            ).hexdigest()
            for name in (
                "protocol.md",
                "stage5b_protocol.md",
                "retrieval_tasks.md",
                "questionnaire.md",
            )
            if (root / "research/evaluation" / name).is_file()
        }
    )
    for filename in (
        "export_methodology_dashboard.py",
        "methodology_completion.py",
        "methodology_quantitative.py",
    ):
        path = root / "scripts" / filename
        if path.is_file():
            hashes["calculation--" + filename] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    source_status = lambda field: source_by_id.get(field.get("source_id"), {}).get(
        "verification_status", "UNKNOWN_SOURCE"
    )
    source_review_status = lambda field: (
        source_review.get(
            source_by_id.get(field.get("source_id"), {}).get("source_code"), {}
        ).get("review_status")
        or "NOT_REVIEWED"
    )
    precise_dates = []
    for source in source_by_id.values():
        value = source.get("source_date")
        try:
            if (
                payload["methodology"]["status"] != "READY"
                or not isinstance(value, str)
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
            ):
                raise ValueError("No approved exact temporal basis")
            source_date, as_of = (
                date.fromisoformat(value),
                date.fromisoformat(base.get("as_of_date") or ""),
            )
            age = (as_of - source_date).days if as_of >= source_date else None
        except (TypeError, ValueError):
            age = None
        precise_dates.append(
            {
                "source_id": source["id"],
                "source_code": source["source_code"],
                "source_date": value,
                "age_days": age,
                "status": "SOURCE_REPORTED"
                if age is not None
                else "PENDING_REVIEW"
                if not base.get("as_of_date")
                else "UNAVAILABLE",
            }
        )
    source_dates = []
    for source in inventories:
        code = source["source_code"]
        registered = next(
            (row for row in source_by_id.values() if row["source_code"] == code), {}
        )
        canonical = registered.get("source_date") or source.get("source_date") or None
        source_dates.append(
            {
                "source_code": code,
                "date_kind": "source_date",
                "date_value": canonical,
                "status": "SOURCE_REPORTED" if canonical else "UNAVAILABLE",
                "basis": "Canonical DB/source inventory metadata; unknown is not replaced by review or upload date.",
            }
        )
        for kind in (
            "document_date",
            "issue_date",
            "revision_date",
            "event_date",
            "coverage_start",
            "coverage_end",
        ):
            value = source_review.get(code, {}).get(kind)
            if isinstance(value, str) and re.fullmatch(
                r"\d{4}(?:-\d{2}(?:-\d{2})?)?", value
            ):
                source_dates.append(
                    {
                        "source_code": code,
                        "date_kind": kind,
                        "date_value": value,
                        "status": "SOURCE_REPORTED",
                        "basis": "Formal source_review date field; original precision retained. Not canonical source age, event admission or present condition.",
                    }
                )
    return {
        "schema_version": SCHEMA,
        "temporal_basis": {
            "snapshot_captured_at": payload["captured_at"],
            "api_read_at": None,
            "dataset_as_of": base.get("as_of_date") or None,
            "dataset_status": payload["methodology"]["dataset_status"],
            "rule": "Snapshot capture, runtime API read time and approved dataset as-of/freeze are separate. API read time is supplied live by the read-only adapter, not imputed into the controlled export. No approved freeze date is asserted.",
        },
        "metric_dictionary": dictionary(),
        "coverage": {"groups": groups, "assets": coverage_assets},
        "field_quality": {
            **quality(all_technical, source_by_id, source_review),
            "units": counts(
                field.get("unit") or "UNSPECIFIED" for field in all_technical
            ),
            "source_status": counts(source_status(field) for field in all_technical),
            "source_review_status": counts(
                source_review_status(field) for field in all_technical
            ),
            "semantics": counts(
                "SOURCE_REPORTED / HISTORICAL_DOCUMENTED"
                if (field.get("reviewed_provenance") or {}).get("verification_level")
                == "L2"
                else "UNREVIEWED_RECORD"
                for field in all_technical
            ),
            "by_asset": quality_assets,
            "by_category": [
                {
                    "category_code": category,
                    **{
                        key: value
                        for key, value in quality(
                            fields, source_by_id, source_review
                        ).items()
                        if key
                        in {
                            "total_fields",
                            "numeric_fields",
                            "text_fields",
                            "missing_value_fields",
                        }
                    },
                }
                for category, fields in sorted(categories.items())
            ],
        },
        "lineage": lineage,
        "retained_review_blockers": register_aggregates(controlled),
        "retrieval_feasibility": task_rows,
        "readiness_groups": compiler_groups(compiler_report),
        "empirical_metrics": empirical_metrics(),
        "source_ages": precise_dates,
        "source_dates": source_dates,
        "input_hashes": hashes,
    }


def write_quantitative_artifacts(quantitative, output):
    """Targeted CSV/JSON artifacts; no duplicate whole methodology snapshot."""
    output.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": SCHEMA,
        "temporal_basis": quantitative["temporal_basis"],
    }
    maim_rows = []
    for asset in quantitative["coverage"]["assets"]:
        maim_rows.append(
            {
                "asset_id": asset["asset_id"],
                "asset_code": asset["asset_code"],
                "scope": asset["scope"],
                **{
                    key: value
                    for key, value in asset["maim"].items()
                    if key
                    not in {"proposed", "proposed_not_applicable", "proposed_semantics"}
                },
                **{
                    "proposed_" + key: value
                    for key, value in (asset["maim"]["proposed"] or {}).items()
                },
            }
        )
    (output / "maim-coverage.json").write_text(
        json.dumps(
            {**metadata, "assets": quantitative["coverage"]["assets"]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    fields = [
        "asset_id",
        "asset_code",
        "scope",
        "status",
        "applicable",
        "present",
        "verified_record",
        "missing",
        "not_applicable",
        "proposed_applicable",
        "proposed_present",
        "proposed_verified_record",
        "proposed_missing",
        "proposed_not_applicable",
        "proposed_unknown",
        "proposed_optional",
    ]
    with (output / "maim-coverage.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(maim_rows)
    asset_metric_rows = [
        {key: value for key, value in asset.items() if key != "maim"}
        for asset in quantitative["coverage"]["assets"]
    ]
    (output / "coverage-metrics.json").write_text(
        json.dumps(
            {
                **metadata,
                "groups": quantitative["coverage"]["groups"],
                "assets": asset_metric_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    coverage = [
        {"scope": group["scope"], "asset_code": "", **metric}
        for group in quantitative["coverage"]["groups"]
        for metric in group["metrics"]
    ]
    coverage += [
        {"scope": asset["scope"], "asset_code": asset["asset_code"], **metric}
        for asset in quantitative["coverage"]["assets"]
        for metric in asset["metrics"]
    ]
    with (output / "coverage-metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "scope",
                "asset_code",
                "metric_id",
                "numerator",
                "denominator",
                "value",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(coverage)
    (output / "metric-dictionary.json").write_text(
        json.dumps(
            {**metadata, "metrics": quantitative["metric_dictionary"]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    names = (
        "maim-coverage.json",
        "maim-coverage.csv",
        "coverage-metrics.json",
        "coverage-metrics.csv",
        "metric-dictionary.json",
    )
    (output / "quantitative-input-hashes.json").write_text(
        json.dumps(
            {
                **metadata,
                "input_hashes": quantitative["input_hashes"],
                "output_sha256": {
                    name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                    for name in names
                },
            },
            indent=2,
        )
        + "\n"
    )
