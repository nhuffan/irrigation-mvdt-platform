"""Compile explicit, reviewed Stage 5B denominators; no DB writes or inferred approvals."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from scripts.research_common import digest, research_code, validate_scope

SPEC = "STAGE-5B-v1"
CHECKS = (
    "study_boundary",
    "target_inventory",
    "maim",
    "source_authority",
    "asset_identity",
    "geometry",
    "dev_separation",
    "checkpoint_a",
    "checkpoint_b",
    "checkpoint_c",
    "checkpoint_d",
)
FIELDS = {
    "identity",
    "category",
    "spatial",
    "technical",
    "condition",
    "inspection",
    "repair",
    "maintenance",
    "source",
    "document",
    "three_d",
}


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def boolean(value):
    if value not in ("true", "false"):
        raise ValueError("Use explicit true/false values in inventories")
    return value == "true"


def base_scope_fingerprint(base):
    return digest(
        {
            key: base.get(key)
            for key in (
                "dataset_version",
                "data_origin",
                "as_of_date",
                "reservoir_ids",
                "record_ids",
                "maim_required",
                "not_applicable",
                "conflict_reviews",
            )
        }
    )


def compile_scope(
    base, targets, sources, requirements, review, acceptance, validate_output=True
):
    errors = []
    fingerprint = base_scope_fingerprint(base)
    if review.get("base_scope_sha256") != fingerprint:
        errors.append(
            "Base scope/record allowlists changed or not reviewed; record their SHA-256"
        )
    for key in ("reviewed_by", "reviewed_at", "study_boundary_reference"):
        if not isinstance(review.get(key), str) or not review[key].strip():
            errors.append(f"Missing review: {key}")
    if review.get("reviewed_at"):
        try:
            if datetime.fromisoformat(review["reviewed_at"]).tzinfo is None:
                raise ValueError()
        except ValueError:
            errors.append("reviewed_at requires an ISO timestamp with timezone")
    if not base.get("dataset_version") or review.get("dataset_version") != base.get(
        "dataset_version"
    ):
        errors.append("Review and scope dataset versions differ")
    for key in CHECKS:
        check = review.get("checks", {}).get(key, {})
        if check.get("status") != "APPROVED" or not check.get("evidence_reference"):
            errors.append(f"Review not approved: {key}")
    included = []
    seen = set()
    for t in targets:
        code = t.get("target_asset_code", "")
        if not research_code(code) or code in seen:
            errors.append("Target code must be unique RS- code")
        seen.add(code)
        if not boolean(t.get("in_scope")):
            if not t.get("notes"):
                errors.append(f"Excluded asset needs rationale: {code}")
            continue
        if t.get("verification_status") != "VERIFIED" or not all(
            t.get(k) for k in ("target_asset_name", "category", "evidence_reference")
        ):
            errors.append(f"Target inventory not verified: {code}")
        if t.get("expected_geometry_type") not in (
            "Point",
            "LineString",
            "Polygon",
            "NONE",
        ):
            errors.append(f"Invalid target geometry type: {code}")
        boolean(t.get("requires_3d"))
        included.append(t)
    if not included:
        errors.append("No approved target inventory; denominator unavailable")
    codes = {t["target_asset_code"] for t in included}
    categories = {t["category"] for t in included}
    for t in included:
        parent = t.get("parent_asset_code")
        if parent and parent not in codes:
            errors.append(f"Parent outside included inventory: {parent}")
        trail = {t["target_asset_code"]}
        parents = {t["target_asset_code"]: t.get("parent_asset_code") for t in included}
        while parent and parent in parents:
            if parent in trail:
                errors.append("Target inventory hierarchy cycle")
                break
            trail.add(parent)
            parent = parents[parent]
    if not sources:
        errors.append("No reviewed source inventory")
    source_codes = []
    expected = []
    allowed = review.get("eligible_source_types", [])
    if not allowed:
        errors.append("Eligible source types not approved")
    for source in sources:
        code = source.get("source_code", "")
        if not research_code(code) or code in source_codes:
            errors.append("Source code must be unique RS- code")
        source_codes.append(code)
        if source.get("source_type") not in allowed:
            errors.append(f"Unapproved source type: {code}")
        if not all(
            source.get(k)
            for k in ("title", "source_owner", "authority_level", "evidence_reference")
        ):
            errors.append(f"Source ownership/evidence missing: {code}")
        if source.get("verification_status") not in (
            "UNVERIFIED",
            "PARTIALLY_VERIFIED",
            "VERIFIED",
            "REJECTED",
        ):
            errors.append("Invalid source verification")
        if boolean(source.get("file_expected")):
            expected.append(code)
        boolean(source.get("file_available"))
        if (
            not set(filter(None, source.get("related_asset_codes", "").split("|")))
            <= codes
        ):
            errors.append("Source references out-of-scope asset")
    field_map = {c: set() for c in categories}
    technical = {c: [] for c in categories}
    rule_keys = set()
    for rule in requirements:
        c = rule.get("category")
        field = rule.get("field")
        attribute = rule.get("attribute_key", "")
        if c not in categories or field not in FIELDS:
            errors.append("Unknown MAIM category or field")
            continue
        key = (c, field, attribute)
        if key in rule_keys:
            errors.append("Duplicate MAIM requirement")
        rule_keys.add(key)
        if not rule.get("evidence_reference"):
            errors.append("MAIM rule requires evidence")
        required = boolean(rule.get("required"))
        if field == "technical" and required:
            if not attribute:
                errors.append("Required technical rule needs an attribute_key")
            technical[c].append(
                {"attribute_key": attribute, "unit": rule.get("expected_unit") or None}
            )
        if required:
            field_map[c].add(field)
    if any(not v for v in field_map.values()):
        errors.append("Every included category needs explicit MAIM requirements")
    # The stable checklist IDs from Stage 5A. Highlight is a documented non-blocker.
    expected_checks = {f"F{i:02d}" for i in range(1, 22)}
    seen_checks = set()
    mandatory_checks = {"F01", "F02", "F03", "F04", "F05", "F06", "F19"}
    if any(boolean(t["requires_3d"]) for t in included):
        mandatory_checks.update({"F12", "F13", "F14", "F16", "F17", "F20", "F21"})
    for row in acceptance:
        check_id = row.get("check_id")
        if check_id not in expected_checks or check_id in seen_checks:
            errors.append("Unknown/duplicate acceptance item")
            continue
        seen_checks.add(check_id)
        if check_id == "F15":
            continue
        if (
            row.get("dataset_version") != base.get("dataset_version")
            or row.get("status") not in ("PASS", "N/A")
            or not all(
                row.get(k) for k in ("evidence_reference", "reviewer", "checked_at")
            )
        ):
            errors.append(f"Browser acceptance pending: {check_id}")
        if check_id in mandatory_checks and row.get("status") != "PASS":
            errors.append(f"Core functional acceptance must pass: {check_id}")
        if row.get("status") == "N/A" and not row.get("notes"):
            errors.append(f"N/A acceptance needs rationale: {check_id}")
    if seen_checks != expected_checks:
        errors.append("Incomplete functional acceptance checklist")
    if errors:
        return {
            "status": "NOT_READY",
            "base_scope_sha256": fingerprint,
            "blockers": sorted(set(errors)),
        }, None
    scope = dict(base)
    scope.update(
        metric_spec_version=SPEC,
        target_asset_codes=[t["target_asset_code"] for t in included],
        source_codes=source_codes,
        expected_document_source_codes=expected,
        three_d_asset_codes=[
            t["target_asset_code"] for t in included if boolean(t["requires_3d"])
        ],
        reviewed_by=review["reviewed_by"],
        inventory_reference=review["checks"]["target_inventory"]["evidence_reference"],
    )
    scope["maim_required_by_asset"] = {
        t["target_asset_code"]: sorted(
            field_map[t["category"]] - {"three_d"}
            | ({"three_d"} if boolean(t["requires_3d"]) else set())
        )
        for t in included
    }
    scope["technical_requirements_by_asset"] = {
        t["target_asset_code"]: technical[t["category"]]
        for t in included
        if technical[t["category"]]
    }
    scope["target_inventory"] = included
    scope["empirical_review"] = {
        "status": "APPROVED",
        "base_scope_sha256": fingerprint,
        "targets": targets,
        "review": review,
        "source_inventory": sources,
        "maim_requirements": requirements,
        "acceptance": acceptance,
        "input_sha256": digest(
            {
                "base_scope_sha256": fingerprint,
                "targets": targets,
                "sources": sources,
                "requirements": requirements,
                "review": review,
                "acceptance": acceptance,
            }
        ),
    }
    if validate_output:
        validate_scope(scope)
    return {
        "status": "READY_TO_FREEZE",
        "target_count": len(included),
        "scope_sha256": digest(scope),
        "note": "Declared evidence and review checks passed; reviewer identity and engineering truth require human assurance.",
    }, scope


def validate_compiled_scope(scope):
    evidence = scope.get("empirical_review", {})
    if evidence.get("status") != "APPROVED":
        raise ValueError("Stage 5B requires approved empirical review")
    try:
        report, expected = compile_scope(
            scope,
            evidence["targets"],
            evidence["source_inventory"],
            evidence["maim_requirements"],
            evidence["review"],
            evidence["acceptance"],
            validate_output=False,
        )
    except (KeyError, TypeError) as error:
        raise ValueError("Incomplete empirical review bundle") from error
    if report["status"] != "READY_TO_FREEZE":
        raise ValueError(
            "Empirical review is not ready: " + "; ".join(report["blockers"])
        )
    for key in (
        "target_asset_codes",
        "source_codes",
        "expected_document_source_codes",
        "three_d_asset_codes",
        "maim_required_by_asset",
        "technical_requirements_by_asset",
        "target_inventory",
        "reviewed_by",
        "inventory_reference",
        "empirical_review",
    ):
        if scope.get(key) != expected.get(key):
            raise ValueError(f"Compiled scope differs from reviewed inputs: {key}")


def main():
    parser = argparse.ArgumentParser()
    for key in (
        "base-scope",
        "targets",
        "sources",
        "maim",
        "review",
        "acceptance",
        "output",
    ):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    report, scope = compile_scope(
        json.loads(args.base_scope.read_text()),
        read_rows(args.targets),
        read_rows(args.sources),
        read_rows(args.maim),
        json.loads(args.review.read_text()),
        read_rows(args.acceptance),
    )
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "readiness.json").write_text(json.dumps(report, indent=2) + "\n")
    if scope:
        (args.output / "scope.json").write_text(json.dumps(scope, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if scope is None:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
