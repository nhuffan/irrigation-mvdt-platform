"""Synthetic methodology fixtures only; no real approval or empirical evidence."""

import csv
import hashlib
import io
import json
from copy import deepcopy

import pytest
from test_empirical import inputs

from scripts.methodology_review import (
    PROTOCOL,
    REQUIRED_GATES,
    ROLES,
    load_methodology,
    package_fingerprint,
)
from scripts.prepare_empirical_scope import (
    base_scope_fingerprint,
    compile_scope,
    validate_compiled_scope,
)
from scripts.research_common import validate_scope

STAMP = {"reviewer": "TEST ONLY", "reviewed_at": "2026-10-11T00:00:00+00:00"}


def put(bundle, name, rows):
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    content = out.getvalue()
    bundle["inputs"][name] = {
        "content": content,
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
    }


def get(bundle, name):
    return list(csv.DictReader(io.StringIO(bundle["inputs"][name]["content"])))


def context(data):
    b, targets, sources, requirements, review, acceptance = data
    return {
        "dataset_version": b["dataset_version"],
        "base_scope_sha256": base_scope_fingerprint(b),
        "record_ids": b["record_ids"],
        "targets": targets,
        "sources": sources,
        "requirements": requirements,
        "review": review,
        "acceptance": acceptance,
        "applicability": [],
    }


def approve(data, bundle):
    bundle["approval"] = {
        **STAMP,
        "status": "APPROVED",
        "reviewer_kind": "HUMAN",
        "package_sha256": package_fingerprint(context(data), bundle),
        "evidence_reference": "TEST synthetic signature",
        "unknown_ownership_acknowledged": True,
        "reviewer_limitations_acknowledged": True,
    }


def fixture():
    data = inputs()
    data[0]["methodology_protocol"] = PROTOCOL
    data[0]["record_ids"]["technical"] = ["00000000-0000-4000-8000-000000000001"]
    data[4]["base_scope_sha256"] = base_scope_fingerprint(data[0])
    data[2][0].update(source_owner="", authority_level="")
    data[-1][14]["status"] = "FAIL"
    b = {
        "protocol": PROTOCOL,
        "dataset_version": data[0]["dataset_version"],
        "inputs": {},
    }
    sr = {
        **STAMP,
        "source_code": "RS-S",
        "authority_class": "SUPPORTING",
        "authority_basis": "TEST",
        "eligibility_basis": "TEST bounded use",
        "evidence_locator": "TEST p1",
        "coverage_basis": "TEST",
        "file_expected": "true",
        "related_asset_codes": "RS-A|RS-B",
        "evidence_ids": "E1",
    }
    for role in ROLES:
        sr["eligible_" + role] = "YES"
    for who in ["owner", "issuer"]:
        sr.update(
            {
                who + "_status": "UNKNOWN",
                who + "_name": "",
                who + "_evidence": "TEST unconfirmed",
            }
        )
    put(b, "source_review", [sr])
    put(b, "evidence_index", [{"evidence_id": "E1", "source_code": "RS-S"}])
    put(
        b,
        "source_boundary_review",
        [
            {
                **STAMP,
                "source_code": "RS-S",
                "evidence_id": "E1",
                "representation_id": "E1",
                "boundary_decision": "IN_SCOPE",
                "reason": "TEST",
            }
        ],
    )
    put(
        b,
        "claim_sources",
        [
            {
                **STAMP,
                "record_kind": "technical",
                "record_id": "00000000-0000-4000-8000-000000000001",
                "role": "technical",
                "source_code": "RS-S",
                "evidence_id": "E1",
                "asset_codes": "RS-A",
                "evidence_locator": "TEST p1",
            }
        ],
    )
    maim = []
    for target in data[1]:
        for rule in data[3] + [
            {"field": "three_d", "attribute_key": "", "required": target["requires_3d"]}
        ]:
            maim.append(
                {
                    **STAMP,
                    "asset_code": target["target_asset_code"],
                    "field": rule["field"],
                    "attribute_key": rule["attribute_key"],
                    "effective_required": rule["required"],
                    "disposition": "REQUIRED"
                    if rule["required"] == "true"
                    else "OPTIONAL",
                    "reason": "TEST",
                    "evidence": "TEST",
                    "methodological_effect": "TEST no weakening",
                }
            )
    put(b, "maim_review", maim)
    put(
        b,
        "reviewer_independence_review",
        [
            {
                **STAMP,
                "review_stage": "TEST",
                "ai_operated": "true",
                "human_reviewed": "false",
                "domain_expert_reviewed": "false",
                "custodian_confirmed": "false",
                "independent_cross_review": "false",
                "highest_level": "L2",
                "evidence": "TEST",
                "limitations": "TEST no independent review",
            }
        ],
    )
    gates = [
        {
            **STAMP,
            "gate_id": gid,
            "required_for_freeze": "true",
            "current_status": "PASS",
            "evidence": "TEST",
            "blocking_reason": "",
            "resolution_path": "",
        }
        for gid in sorted(REQUIRED_GATES)
    ]
    gates += [
        {
            **STAMP,
            "gate_id": r["check_id"],
            "required_for_freeze": "false" if r["check_id"] == "F15" else "true",
            "current_status": r["status"],
            "evidence": "TEST",
            "blocking_reason": "TEST highlight only" if r["check_id"] == "F15" else "",
            "resolution_path": "TEST disclose",
        }
        for r in data[-1]
    ]
    put(b, "readiness_gates", gates)
    approve(data, b)
    return data, b


def test_mc_unknown_ownership_can_be_explicitly_governed_without_promotion():
    data, b = fixture()
    report, s = compile_scope(*data, methodology=b)
    assert report["status"] == "READY_TO_FREEZE"
    assert s["expected_document_source_codes"] == ["RS-S"]
    assert s["empirical_review"]["source_inventory"][0]["source_owner"] == ""
    validate_scope(s)
    assert "methodology_package_sha256" in s["empirical_review"]


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("source_review", "authority_class", "UNKNOWN_AUTHORITY"),
        ("source_review", "eligible_technical", "NO"),
        ("source_review", "file_expected", "false"),
        ("source_review", "source_code", "DEV-S"),
        ("source_review", "evidence_ids", "MISSING"),
        ("source_review", "owner_status", "VERIFIED"),
        ("source_boundary_review", "boundary_decision", "OUT_OF_SCOPE_REPRESENTATION"),
        ("source_boundary_review", "boundary_decision", "DUPLICATE_REPRESENTATION"),
        ("source_boundary_review", "source_code", "RS-OTHER"),
        ("claim_sources", "asset_codes", "DEV-A"),
        ("claim_sources", "evidence_id", "MISSING"),
        ("claim_sources", "record_id", "unscoped"),
        ("claim_sources", "role", "reference"),
        ("maim_review", "effective_required", "false"),
        ("maim_review", "disposition", "NOT_APPLICABLE"),
        ("reviewer_independence_review", "highest_level", "L3"),
        ("reviewer_independence_review", "independent_cross_review", "maybe"),
        ("readiness_gates", "current_status", "PENDING"),
        ("readiness_gates", "required_for_freeze", "false"),
    ],
)
def test_invalid_mc_decisions_block_even_with_fresh_declared_approval(
    table, field, value
):
    data, b = fixture()
    records = get(b, table)
    records[0][field] = value
    put(b, table, records)
    approve(data, b)
    report, s = compile_scope(*data, methodology=b)
    assert report["status"] == "NOT_READY" and s is None


@pytest.mark.parametrize(
    "table",
    [
        "source_review",
        "source_boundary_review",
        "readiness_gates",
        "maim_review",
        "claim_sources",
    ],
)
def test_duplicate_reviews_rejected(table):
    data, b = fixture()
    records = get(b, table)
    put(b, table, records + [records[0]])
    approve(data, b)
    assert compile_scope(*data, methodology=b)[1] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "PENDING"),
        ("reviewer_kind", "AI"),
        ("package_sha256", "old"),
        ("reviewed_at", "2026-10-11"),
        ("unknown_ownership_acknowledged", False),
        ("reviewer_limitations_acknowledged", False),
    ],
)
def test_approval_is_human_declared_current_and_explicit(field, value):
    data, b = fixture()
    b["approval"][field] = value
    assert compile_scope(*data, methodology=b)[1] is None


def test_bundle_required_and_stale_scope_approval_not_reused():
    data, b = fixture()
    assert compile_scope(*data)[1] is None
    del data[0]["methodology_protocol"]
    assert compile_scope(*data, methodology=b)[1] is None


def test_changed_claim_or_source_file_cannot_reuse_approval():
    data, b = fixture()
    records = get(b, "source_review")
    records[0]["authority_basis"] = "Changed reviewed evidence"
    put(b, "source_review", records)
    assert compile_scope(*data, methodology=b)[1] is None
    approve(data, b)
    assert compile_scope(*data, methodology=b)[1] is not None


def test_f02_cannot_be_hidden_by_gate_inventory():
    data, b = fixture()
    data[-1][1]["status"] = "FAIL"
    approve(data, b)
    report, s = compile_scope(*data, methodology=b)
    assert s is None
    assert "MC: functional gate differs from acceptance: F02" in report["blockers"]


def test_scope_replay_rejects_removed_or_mutated_mc_evidence():
    data, b = fixture()
    _, scope = compile_scope(*data, methodology=b)
    for action in ["remove", "mutate", "strip"]:
        changed = deepcopy(scope)
        if action == "remove":
            del changed["empirical_review"]["methodology"]
        elif action == "strip":
            del changed["methodology_protocol"]
        else:
            changed["empirical_review"]["methodology"]["inputs"]["source_review"][
                "content"
            ] += "tampered"
        with pytest.raises(ValueError):
            validate_compiled_scope(changed)


def test_loader_checks_actual_csv_bytes_and_offline_replay(tmp_path):
    data, bundle = fixture()
    declaration = {k: v for k, v in bundle.items() if k != "inputs"}
    declaration["files"] = {}
    for key, entry in bundle["inputs"].items():
        path = tmp_path / (key + ".csv")
        path.write_bytes(entry["content"].encode())
        declaration["files"][key] = {"path": path.name, "sha256": entry["sha256"]}
    manifest = tmp_path / "methodology.json"
    manifest.write_text(json.dumps(declaration))
    loaded = load_methodology(manifest)
    assert loaded == bundle
    assert compile_scope(*data, methodology=loaded)[1] is not None
    (tmp_path / "source_review.csv").write_text("changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        load_methodology(manifest)


def test_legacy_compilation_still_replays_without_mc_opt_in():
    report, scope = compile_scope(*inputs())
    assert report["status"] == "READY_TO_FREEZE"
    validate_scope(scope)


def component_mc_fixture():
    """Synthetic supplementary child; no real inventory or reviewer decisions."""
    data, bundle = fixture()
    data[0]["component_scope"] = {
        "version": "COMPONENT-SCOPE-v1",
        "primary_sample_count": 2,
        "inventory_evidence": "TEST synthetic child inventory",
        "technical_evidence": "TEST synthetic child record",
        "components": [
            {
                "asset_code": "RS-CHILD",
                "asset_id": "00000000-0000-4000-8000-000000000020",
                "parent_asset_code": "RS-A",
                "parent_asset_id": "00000000-0000-4000-8000-000000000010",
                "technical_record_ids": ["00000000-0000-4000-8000-000000000002"],
            }
        ],
    }
    data[4]["base_scope_sha256"] = base_scope_fingerprint(data[0])
    approve(data, bundle)
    return data, bundle


def test_mc_supplementary_scope_preserves_primary_claim_and_maim_denominators():
    data, bundle = component_mc_fixture()
    report, compiled = compile_scope(*data, methodology=bundle)
    assert report["status"] == "READY_TO_FREEZE"  # Synthetic declarations only.
    assert compiled["target_asset_codes"] == ["RS-A", "RS-B"]
    assert set(compiled["maim_required_by_asset"]) == {"RS-A", "RS-B"}
    assert compiled["record_ids"]["technical"] == [
        "00000000-0000-4000-8000-000000000001"
    ]
    assert compiled["component_scope"]["components"][0]["technical_record_ids"] == [
        "00000000-0000-4000-8000-000000000002"
    ]


@pytest.mark.parametrize("formal_coverage", ["RS-CHILD", ""])
def test_mc_component_source_review_separates_inventory_from_primary_coverage(
    formal_coverage,
):
    data, bundle = component_mc_fixture()
    child_source = deepcopy(data[2][0])
    child_source.update(source_code="RS-CHILD-SOURCE", related_asset_codes="RS-CHILD")
    data[2].append(child_source)
    source_review = deepcopy(get(bundle, "source_review")[0])
    source_review.update(
        source_code="RS-CHILD-SOURCE",
        related_asset_codes=formal_coverage,
        coverage_basis="TEST child inventory retained; no primary coverage if empty",
        evidence_ids="E-CHILD",
    )
    if not formal_coverage:
        source_review["eligible_technical"] = "NO"
    put(bundle, "source_review", get(bundle, "source_review") + [source_review])
    put(
        bundle,
        "evidence_index",
        get(bundle, "evidence_index")
        + [{"evidence_id": "E-CHILD", "source_code": "RS-CHILD-SOURCE"}],
    )
    boundary = deepcopy(get(bundle, "source_boundary_review")[0])
    boundary.update(
        source_code="RS-CHILD-SOURCE",
        evidence_id="E-CHILD",
        representation_id="E-CHILD",
    )
    put(
        bundle,
        "source_boundary_review",
        get(bundle, "source_boundary_review") + [boundary],
    )
    approve(data, bundle)
    report, compiled = compile_scope(*data, methodology=bundle)
    assert "Source references out-of-scope asset" not in report.get("blockers", [])
    if formal_coverage:
        assert compiled is None
        assert (
            "MC: source coverage outside targets: RS-CHILD-SOURCE" in report["blockers"]
        )
    else:
        # An explicitly reviewed zero-primary-coverage view is not parent evidence.
        assert report["status"] == "READY_TO_FREEZE"  # Synthetic fixture only.
        assert compiled["target_asset_codes"] == ["RS-A", "RS-B"]
        claim = get(bundle, "claim_sources")[0]
        claim.update(source_code="RS-CHILD-SOURCE", evidence_id="E-CHILD")
        put(bundle, "claim_sources", [claim])
        approve(data, bundle)
        report, compiled = compile_scope(*data, methodology=bundle)
        assert compiled is None
        assert any(
            "MC: claim asset coverage unconfirmed:" in error
            for error in report["blockers"]
        )
        assert any(
            "MC: source ineligible for claim role:" in error
            for error in report["blockers"]
        )


@pytest.mark.parametrize("claim_asset", ["RS-CHILD", "RS-A"])
def test_mc_child_claim_not_admitted_by_component_scope_or_parent_relabel(claim_asset):
    data, bundle = component_mc_fixture()
    child_claim = deepcopy(get(bundle, "claim_sources")[0])
    child_claim.update(
        record_id="00000000-0000-4000-8000-000000000002",
        asset_codes=claim_asset,
    )
    put(bundle, "claim_sources", get(bundle, "claim_sources") + [child_claim])
    approve(data, bundle)
    report, compiled = compile_scope(*data, methodology=bundle)
    assert compiled is None
    assert any(
        "MC: unknown/duplicate scoped claim:" in error
        and "00000000-0000-4000-8000-000000000002" in error
        for error in report["blockers"]
    )
    assert data[0]["record_ids"]["technical"] == [
        "00000000-0000-4000-8000-000000000001"
    ]


def test_mc_child_record_cannot_overlap_primary_allowlist_despite_fresh_declaration():
    data, bundle = component_mc_fixture()
    data[0]["record_ids"]["technical"].append("00000000-0000-4000-8000-000000000002")
    data[4]["base_scope_sha256"] = base_scope_fingerprint(data[0])
    approve(data, bundle)
    report, compiled = compile_scope(*data, methodology=bundle)
    assert compiled is None
    assert (
        "Component scope: Duplicate/primary component technical record"
        in report["blockers"]
    )


def test_mc_component_with_unknown_parent_is_rejected_without_reparenting():
    data, bundle = component_mc_fixture()
    child = data[0]["component_scope"]["components"][0]
    child["parent_asset_code"] = "RS-UNKNOWN-PARENT"
    data[4]["base_scope_sha256"] = base_scope_fingerprint(data[0])
    approve(data, bundle)
    report, compiled = compile_scope(*data, methodology=bundle)
    assert compiled is None
    assert "Component scope: Invalid component identity/parent" in report["blockers"]
    assert child["parent_asset_code"] == "RS-UNKNOWN-PARENT"


def test_child_measurement_does_not_fill_parent_technical_requirement():
    from test_empirical import empirical_sample

    from scripts.evaluate_research_dataset import evaluate

    snapshot = empirical_sample()
    baseline = evaluate(snapshot)["metrics"]["technical_coverage"]
    child = deepcopy(snapshot["assets"][0])
    child.update(id="synthetic-child", asset_code="RS-CHILD", parent_asset_id="a")
    snapshot["assets"].append(child)
    measurement = deepcopy(snapshot["records"]["technical"][0])
    measurement.update(
        id="synthetic-child-height",
        asset_id="synthetic-child",
        attribute_key="height",
        value_number=0,
    )
    snapshot["records"]["technical"].append(measurement)
    result = evaluate(snapshot)
    assert result["metrics"]["technical_coverage"] == baseline
    assert baseline["denominator"] == 2 and baseline["value"] == 0
    assert (
        next(
            row
            for row in result["technical_requirements"]
            if row["asset_code"] == "RS-A" and row["attribute_key"] == "height"
        )["available"]
        is False
    )
    assert {row["asset_code"] for row in result["completeness"]} == {"RS-A", "RS-B"}
