"""Versioned source/MC gates; validates declarations, never authenticates reviewers."""

import csv
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path

from scripts.research_common import digest

PROTOCOL = "STAGE-5B-MC-v1"
APPROVAL_POLICY = "ROLE_SCOPED-v1"
APPROVAL_ROLES = {
    "RESEARCHER_APPROVAL": "RESEARCHER",
    "DOMAIN_REVIEW": "DOMAIN_EXPERT",
    "CUSTODIAN_CONFIRMATION": "CUSTODIAN",
    "INDEPENDENT_REVIEW": "INDEPENDENT_REVIEWER",
}
REQUIRED_APPROVALS = {
    ("RESEARCHER_APPROVAL", "METHODOLOGY_PACKAGE"),
    ("DOMAIN_REVIEW", "MAIM"),
}
TABLES = {
    "source_review",
    "source_boundary_review",
    "reviewer_independence_review",
    "readiness_gates",
    "maim_review",
    "evidence_index",
    "claim_sources",
}
REQUIRED_GATES = {
    "MC_SCOPE",
    "MC_BOUNDARY",
    "MC_SOURCE_POLICY",
    "MC_MAIM",
    "MC_REVIEWER",
    "MC_APPROVAL",
    "MC_INTEGRITY",
    "MC_PROVENANCE",
    "MC_HASHES",
}
ROLES = {
    "identity",
    "geometry",
    "technical",
    "condition",
    "inspection",
    "repair",
    "maintenance",
    "document",
    "3d",
    "reference",
}
CLAIM_ROLES = {
    "technical": "technical",
    "conditions": "condition",
    "inspections": "inspection",
    "repairs": "repair",
    "maintenance": "maintenance",
    "documents": "document",
    "models": "3d",
    "model_asset_links": "3d",
}
AUTHORITY = {
    "AUTHORITATIVE",
    "SUPPORTING",
    "REFERENCE",
    "UNKNOWN_AUTHORITY",
    "NOT_ELIGIBLE",
}
BOUNDARIES = {
    "IN_SCOPE",
    "REFERENCE_ONLY",
    "OUT_OF_SCOPE_REPRESENTATION",
    "DUPLICATE_REPRESENTATION",
    "DIFFERENT_REVISION",
    "UNRESOLVED",
}


def load_methodology(path):
    """Read exact checksummed CSV bytes, embedding them for offline freeze replay."""
    path = Path(path)
    declaration = json.loads(path.read_text())
    files = declaration.pop("files")
    if set(files) != TABLES:
        raise ValueError("MC requires the complete set of formal input files")
    declaration["inputs"] = {}
    for name, entry in files.items():
        raw = (path.parent / entry["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError(f"MC input file checksum mismatch: {name}")
        declaration["inputs"][name] = {
            "sha256": entry["sha256"],
            "content": raw.decode("utf-8-sig"),
        }
        # Preserve BOM bytes in the embedded content as well as the disk checksum.
        declaration["inputs"][name]["content"] = raw.decode("utf-8")
    if "closure_files" in declaration:
        declaration["closure_inputs"] = {}
        for name, entry in declaration.pop("closure_files").items():
            raw = (path.parent / entry["path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise ValueError(f"MC-R closure checksum mismatch: {name}")
            declaration["closure_inputs"][name] = {
                "sha256": entry["sha256"],
                "content": raw.decode("utf-8"),
            }
    return declaration


def package_fingerprint(context, methodology):
    return digest(
        {
            "protocol": PROTOCOL,
            "compiler_context": context,
            "methodology": {k: v for k, v in methodology.items() if k != "approval"},
        }
    )


def timestamp(value):
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except (TypeError, ValueError):
        return False


def reviewed(row):
    return bool(row.get("reviewer", "").strip()) and timestamp(row.get("reviewed_at"))


def validate_role_approvals(approval, fingerprint):
    """Validate scoped declarations, not the real-world identity of a signer."""
    errors = []
    accepted, seen = set(), set()
    entries = approval.get("entries", []) if isinstance(approval, dict) else None
    if not isinstance(entries, list):
        return ["MC-R: approval entries must be a list"]
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("MC-R: malformed approval entry")
            continue
        kind, scope = entry.get("approval_type"), entry.get("scope")
        if not isinstance(kind, str) or not isinstance(scope, str) or not scope.strip():
            errors.append("MC-R: missing approval type/scope")
            continue
        key = (kind, scope)
        valid = (
            key not in seen
            and kind in APPROVAL_ROLES
            and entry.get("reviewer_role") == APPROVAL_ROLES.get(kind)
            and entry.get("package_fingerprint") == fingerprint
            and isinstance(entry.get("reviewer_name"), str)
            and bool(entry["reviewer_name"].strip())
            and timestamp(entry.get("reviewed_at"))
            and isinstance(entry.get("evidence"), str)
            and bool(entry["evidence"].strip())
            and entry.get("limitations_acknowledged") is True
            and entry.get("decision") == "APPROVED"
        )
        seen.add(key)
        if valid:
            accepted.add(key)
        else:
            errors.append(
                f"MC-R: invalid/stale/duplicate scoped approval: {kind}/{scope}"
            )
    for kind, scope in sorted(REQUIRED_APPROVALS - accepted):
        errors.append(f"MC-R: required scoped approval pending: {kind}/{scope}")
    return errors


def validate_methodology(context, methodology):
    """Fail closed on missing/invalid evidence, stale approvals and claim exclusions."""
    errors = []
    fail = errors.append
    fingerprint = package_fingerprint(context, methodology)
    if methodology.get("protocol") != PROTOCOL:
        fail("MC: unsupported methodology protocol")
    if methodology.get("dataset_version") != context["dataset_version"]:
        fail("MC: dataset version mismatch")
    inputs = methodology.get("inputs", {})
    if set(inputs) != TABLES:
        return ["MC: incomplete formal input bundle"], fingerprint
    tables = {}
    for name, entry in inputs.items():
        content = entry.get("content")
        if not isinstance(content, str) or hashlib.sha256(
            content.encode()
        ).hexdigest() != entry.get("sha256"):
            fail(f"MC: input checksum mismatch: {name}")
            continue
        reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
        if not reader.fieldnames or len(reader.fieldnames) != len(
            set(reader.fieldnames)
        ):
            fail(f"MC: invalid CSV header: {name}")
            continue
        tables[name] = list(reader)
        if any(
            None in row or any(v is None for v in row.values()) for row in tables[name]
        ):
            fail(f"MC: malformed CSV row: {name}")
    if errors:
        return errors, fingerprint

    def index(name, key):
        result = {}
        for row in tables[name]:
            code = row.get(key, "")
            if not code or code in result:
                fail(f"MC: missing/duplicate {key}: {name}")
            result[code] = row
        return result

    sources = {s["source_code"]: s for s in context["sources"]}
    targets = {
        t["target_asset_code"]: t for t in context["targets"] if t["in_scope"] == "true"
    }
    sr = index("source_review", "source_code")
    evidence = index("evidence_index", "evidence_id")
    if set(sr) != set(sources):
        fail("MC: source review must cover exactly the controlled sources")
    for eid, e in evidence.items():
        if e.get("source_code") not in sources:
            fail(f"MC: evidence source outside inventory: {eid}")
    for code, row in sr.items():
        if row.get("authority_class") not in AUTHORITY or not reviewed(row):
            fail(f"MC: invalid source authority/reviewer: {code}")
        if any(
            row.get("eligible_" + role) not in {"YES", "NO", "UNRESOLVED"}
            for role in ROLES
        ):
            fail(f"MC: invalid source role eligibility: {code}")
        if any(
            not row.get(k)
            for k in [
                "authority_basis",
                "eligibility_basis",
                "evidence_locator",
                "coverage_basis",
            ]
        ):
            fail(f"MC: source decision lacks basis/locator: {code}")
        if row.get("file_expected") != sources.get(code, {}).get("file_expected"):
            fail(f"MC: expected-source denominator changed: {code}")
        if not set(filter(None, row.get("related_asset_codes", "").split("|"))) <= set(
            targets
        ):
            fail(f"MC: source coverage outside targets: {code}")
        for role in ["owner", "issuer"]:
            status = row.get(role + "_status")
            if status not in {
                "UNKNOWN",
                "PARTIALLY_VERIFIED",
                "VERIFIED",
            } or not row.get(role + "_evidence"):
                fail(f"MC: missing {role} review: {code}")
            if status != "UNKNOWN" and not row.get(role + "_name"):
                fail(f"MC: named {role} missing: {code}")
        for eid in filter(None, row.get("evidence_ids", "").split("|")):
            if evidence.get(eid, {}).get("source_code") != code:
                fail(f"MC: source/evidence mismatch: {code}/{eid}")

    boundary = index("source_boundary_review", "representation_id")
    by_evidence = {}
    covered_sources = set()
    for rid, row in boundary.items():
        code, eid = row.get("source_code"), row.get("evidence_id")
        covered_sources.add(code)
        if (
            code not in sources
            or row.get("boundary_decision") not in BOUNDARIES
            or not reviewed(row)
            or not row.get("reason")
        ):
            fail(f"MC: invalid source boundary: {rid}")
        if eid:
            if eid in by_evidence or evidence.get(eid, {}).get("source_code") != code:
                fail(f"MC: boundary/evidence mismatch or duplicate: {rid}")
            by_evidence[eid] = row
    if set(by_evidence) != set(evidence) or covered_sources != set(sources):
        fail("MC: boundaries must cover every indexed evidence and logical source")

    expected_claims = {
        (kind, rid) for kind, ids in context["record_ids"].items() for rid in ids
    }
    seen_claims = set()
    for row in tables["claim_sources"]:
        key = (row.get("record_kind"), row.get("record_id"))
        role = CLAIM_ROLES.get(key[0])
        code, eid = row.get("source_code"), row.get("evidence_id")
        source = sr.get(code, {})
        if key in seen_claims or key not in expected_claims or role is None:
            fail(f"MC: unknown/duplicate scoped claim: {key}")
        seen_claims.add(key)
        if row.get("role") != role or evidence.get(eid, {}).get("source_code") != code:
            fail(f"MC: invalid claim provenance: {key}")
        if by_evidence.get(eid, {}).get("boundary_decision") != "IN_SCOPE":
            fail(f"MC: claim uses excluded/unresolved representation: {key}")
        allowed = {"AUTHORITATIVE", "SUPPORTING"}
        if role in {"document", "3d"}:
            allowed.add("REFERENCE")
        if (
            source.get("eligible_" + str(role)) != "YES"
            or source.get("authority_class") not in allowed
        ):
            fail(f"MC: source ineligible for claim role: {key}/{code}/{role}")
        assets = set(filter(None, row.get("asset_codes", "").split("|")))
        coverage = set(filter(None, source.get("related_asset_codes", "").split("|")))
        if not assets or not assets <= set(targets) or not assets <= coverage:
            fail(f"MC: claim asset coverage unconfirmed: {key}")
        if not reviewed(row) or not row.get("evidence_locator"):
            fail(f"MC: claim lacks reviewer/locator: {key}")
    if seen_claims != expected_claims:
        fail("MC: provenance review must cover every scoped record exactly once")

    # Review completeness and applicability separately from empirical completeness.
    expected_maim = {}
    for code, target in targets.items():
        for rule in context["requirements"]:
            if rule["category"] == target["category"] and rule["field"] != "three_d":
                expected_maim[(code, rule["field"], rule.get("attribute_key", ""))] = (
                    rule["required"]
                )
        expected_maim[(code, "three_d", "")] = target["requires_3d"]
    seen_maim = set()
    for row in tables["maim_review"]:
        key = (row.get("asset_code"), row.get("field"), row.get("attribute_key", ""))
        req = expected_maim.get(key)
        if key in seen_maim or req is None or row.get("effective_required") != req:
            fail(f"MC: MAIM scope mismatch: {key}")
        seen_maim.add(key)
        allowed = (
            {"REQUIRED", "PENDING_EVIDENCE"}
            if req == "true"
            else {"OPTIONAL", "PENDING_EVIDENCE"}
        )
        if key[1] == "three_d" and req == "false":
            allowed.add("NOT_APPLICABLE")
        if (
            row.get("disposition") not in allowed
            or not reviewed(row)
            or not all(
                row.get(k) for k in ["reason", "evidence", "methodological_effect"]
            )
        ):
            fail(f"MC: incomplete MAIM review: {key}")
    if seen_maim != set(expected_maim):
        fail("MC: MAIM review must cover each target requirement and 3D applicability")

    independence = index("reviewer_independence_review", "review_stage")
    if not independence:
        fail("MC: reviewer provenance missing")
    for stage, row in independence.items():
        flags = [
            "ai_operated",
            "human_reviewed",
            "domain_expert_reviewed",
            "custodian_confirmed",
            "independent_cross_review",
        ]
        if (
            any(row.get(k) not in {"true", "false"} for k in flags)
            or not reviewed(row)
            or not row.get("evidence")
            or not row.get("limitations")
        ):
            fail(f"MC: incomplete reviewer provenance: {stage}")
        if row.get("highest_level") not in {"L0", "L1", "L2", "L3", "NOT_APPLICABLE"}:
            fail(f"MC: unknown verification level: {stage}")
        if row.get("highest_level") == "L3" and (
            row.get("domain_expert_reviewed") != "true"
            and row.get("independent_cross_review") != "true"
        ):
            fail(f"MC: L3 lacks domain/independent review: {stage}")

    gates = index("readiness_gates", "gate_id")
    required = REQUIRED_GATES | {f"F{i:02d}" for i in range(1, 22)}
    if not required <= set(gates):
        fail("MC: incomplete readiness gate inventory")
    acceptance = {row["check_id"]: row for row in context["acceptance"]}
    for gid, row in gates.items():
        expected_required = "false" if gid == "F15" else "true"
        if gid in required and row.get("required_for_freeze") != expected_required:
            fail(f"MC: required gate cannot be disabled: {gid}")
        status = row.get("current_status")
        if row.get("required_for_freeze") not in {"true", "false"} or status not in {
            "PASS",
            "FAIL",
            "PENDING",
            "UNRESOLVED",
            "N/A",
        }:
            fail(f"MC: invalid gate state: {gid}")
        if not reviewed(row) or not row.get("evidence"):
            fail(f"MC: gate lacks review evidence: {gid}")
        if status not in {"PASS", "N/A"} and (
            not row.get("blocking_reason") or not row.get("resolution_path")
        ):
            fail(f"MC: gate lacks resolution path: {gid}")
        if gid in acceptance and status != acceptance[gid]["status"]:
            fail(f"MC: functional gate differs from acceptance: {gid}")
        if row.get("required_for_freeze") == "true" and not (
            status == "PASS" or (gid in acceptance and status == "N/A")
        ):
            fail(f"MC: required gate unresolved: {gid}")

    candidate_review = methodology.get("candidate_evidence_review")
    if candidate_review is not None:
        review_files = candidate_review.get("reviews", {})
        if set(review_files) != {
            "maintenance_2021_2025_review.csv",
            "maintenance_asset_mapping_review.csv",
        }:
            fail("AR-FV-R1: incomplete maintenance candidate review")
        for name, entry in review_files.items():
            content = entry.get("content")
            if not isinstance(content, str) or hashlib.sha256(
                content.encode()
            ).hexdigest() != entry.get("sha256"):
                fail(f"AR-FV-R1: candidate review checksum mismatch: {name}")

    approval = methodology.get("approval", {})
    policy = methodology.get("approval_policy")
    if policy is not None:
        if policy != APPROVAL_POLICY:
            fail("MC-R: unsupported approval policy")
        else:
            errors.extend(validate_role_approvals(approval, fingerprint))
        closure = methodology.get("closure_inputs", {})
        expected = {
            "mc_r_gate_resolution",
            "researcher_methodology_confirmation",
            "maim_closure_review",
            "ai_consistency_review",
        }
        if set(closure) != expected:
            fail("MC-R: incomplete closure review bundle")
        for name, entry in closure.items():
            content = entry.get("content")
            if not isinstance(content, str) or hashlib.sha256(
                content.encode()
            ).hexdigest() != entry.get("sha256"):
                fail(f"MC-R: closure checksum mismatch: {name}")
    elif (
        approval.get("status") != "APPROVED"
        or approval.get("package_sha256") != fingerprint
        or approval.get("reviewer_kind") not in {"HUMAN", "DOMAIN_EXPERT", "CUSTODIAN"}
        or not reviewed(approval)
        or not approval.get("evidence_reference")
        or approval.get("unknown_ownership_acknowledged") is not True
        or approval.get("reviewer_limitations_acknowledged") is not True
    ):
        fail("MC: human methodology approval missing/stale for current package")
    return sorted(set(errors)), fingerprint
