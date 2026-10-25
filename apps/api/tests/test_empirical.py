"""All values below are synthetic fixtures, never case-study observations."""

from copy import deepcopy
from uuid import uuid4

import pytest
from test_research import observation, sample, scope

from scripts.evaluate_research_dataset import evaluate
from scripts.export_research_results import summarize_retrieval, summarize_usability
from scripts.prepare_empirical_scope import (
    CHECKS,
    base_scope_fingerprint,
    compile_scope,
)
from scripts.research_common import validate_scope


def inputs():
    base = scope()
    base["not_applicable"] = {}
    targets = [
        {
            "target_asset_code": code,
            "target_asset_name": code,
            "category": "C",
            "parent_asset_code": "",
            "expected_geometry_type": "Point",
            "in_scope": "true",
            "verification_status": "VERIFIED",
            "requires_3d": "true" if code == "RS-A" else "false",
            "evidence_reference": "TEST ONLY",
        }
        for code in ["RS-A", "RS-B"]
    ]
    sources = [
        {
            "source_code": "RS-S",
            "source_type": "DRAWING",
            "title": "TEST ONLY",
            "source_owner": "TEST",
            "authority_level": "TEST ONLY",
            "verification_status": "VERIFIED",
            "related_asset_codes": "RS-A|RS-B",
            "file_expected": "true",
            "file_available": "false",
            "evidence_reference": "TEST ONLY",
        }
    ]
    requirements = [
        {
            "category": "C",
            "field": field,
            "required": "true",
            "attribute_key": key,
            "expected_unit": unit,
            "evidence_reference": "TEST ONLY",
        }
        for field, key, unit in [
            ("identity", "", ""),
            ("spatial", "", ""),
            ("technical", "width", "m"),
            ("technical", "height", "m"),
            ("document", "", ""),
            ("maintenance", "", ""),
        ]
    ]
    review = {
        "dataset_version": base["dataset_version"],
        "reviewed_by": "TEST ONLY",
        "reviewed_at": "2026-10-06T00:00:00+00:00",
        "study_boundary_reference": "TEST ONLY",
        "eligible_source_types": ["DRAWING"],
        "base_scope_sha256": base_scope_fingerprint(base),
        "checks": {
            key: {"status": "APPROVED", "evidence_reference": "TEST ONLY"}
            for key in CHECKS
        },
    }
    acceptance = [
        {
            "check_id": f"F{i:02d}",
            "dataset_version": base["dataset_version"],
            "status": "PASS" if i != 15 else "NOT_TESTED",
            "evidence_reference": "TEST ONLY",
            "reviewer": "TEST",
            "checked_at": "2026-10-06T00:00:00+00:00",
            "notes": "",
        }
        for i in range(1, 22)
    ]
    return base, targets, sources, requirements, review, acceptance


def compiled():
    report, s = compile_scope(*inputs())
    assert report["status"] == "READY_TO_FREEZE"
    return s


def empirical_sample():
    s = sample()
    s["scope"] = compiled()
    s["assets"][0].update(
        geometry={"type": "Point", "coordinates": [106, 11]}, category_code="C"
    )
    s["models"][0].update(
        source_id="s",
        verification_status="UNVERIFIED",
        coordinate_mode="MANUAL_PLACEMENT",
        longitude=106,
        latitude=11,
        height=0,
        heading=0,
        pitch=0,
        roll=0,
        scale=1,
    )
    s["models"][0]["file_evidence"]["accessible"] = True
    return s


def test_compile_retains_missing_targets_and_file_expectations():
    s = compiled()
    assert s["target_asset_codes"] == ["RS-A", "RS-B"]
    assert s["expected_document_source_codes"] == ["RS-S"]
    assert s["three_d_asset_codes"] == ["RS-A"]
    assert len(s["technical_requirements_by_asset"]["RS-A"]) == 2
    validate_scope(s)


@pytest.mark.parametrize("check", CHECKS)
def test_pending_human_check_blocks_scope(check):
    values = list(inputs())
    values[4]["checks"][check]["status"] = "PENDING"
    report, s = compile_scope(*values)
    assert report["status"] == "NOT_READY" and s is None


def test_stop_conditions_and_browser_acceptance():
    values = list(inputs())
    values[1][0]["target_asset_code"] = "DEV-A"
    assert compile_scope(*values)[0]["status"] == "NOT_READY"
    values = list(inputs())
    values[2][0]["source_owner"] = ""
    assert compile_scope(*values)[0]["status"] == "NOT_READY"
    values = list(inputs())
    values[5][0]["status"] = "N/A"
    values[5][0]["notes"] = "skip"
    assert compile_scope(*values)[0]["status"] == "NOT_READY"
    values = list(inputs())
    values[5][6]["status"] = "N/A"
    values[5][6]["notes"] = "No PDF exists in this fixture"
    assert compile_scope(*values)[0]["status"] == "READY_TO_FREEZE"


def test_tampered_denominator_or_allowlist_needs_new_review():
    s = compiled()
    s["target_asset_codes"].pop()
    with pytest.raises(ValueError):
        validate_scope(s)
    s = compiled()
    s["record_ids"]["inspections"] = [str(uuid4())]
    with pytest.raises(ValueError):
        validate_scope(s)


def test_stage5b_denominators_and_required_attributes():
    s = empirical_sample()
    r = evaluate(s)
    m = r["metrics"]
    assert r["metric_spec_version"] == "STAGE-5B-v1"
    assert m["gis_mapping"]["value"] == 0.5 and m["gis_mapping"]["denominator"] == 2
    assert (
        m["technical_coverage"]["value"] == 0
        and m["technical_coverage"]["denominator"] == 2
    )
    assert m["conditions_coverage"]["denominator"] == 2
    assert m["maintenance_coverage"]["denominator"] == 2
    assert m["repairs_coverage"]["value"] is None
    assert (
        m["three_d_coverage"]["value"] == 0
    )  # UNVERIFIED mapping cannot support the research numerator.
    assert any(
        x["field"] == "document" and x["asset_code"] == "RS-B"
        for x in r["missing_fields"]
    )
    new = deepcopy(s["records"]["technical"][0])
    new.update(id="t3", attribute_key="height", value_number=0)
    s["records"]["technical"].append(new)
    assert evaluate(s)["metrics"]["technical_coverage"]["value"] == 0.5
    new["unit"] = "cm"
    assert evaluate(s)["metrics"]["technical_coverage"]["value"] == 0


def test_latest_verified_condition_and_geometry_type():
    s = empirical_sample()
    s["records"]["conditions"] = [
        {
            "id": "old",
            "asset_id": "a",
            "condition_date": "2024-01-01",
            "condition_status": "OLD",
            "verification_status": "VERIFIED",
            "source_id": "s",
        },
        {
            "id": "latest",
            "asset_id": "a",
            "condition_date": "2025-01-01",
            "condition_status": "REVIEW",
            "verification_status": "VERIFIED",
            "source_id": "s",
        },
        {
            "id": "newer-unverified",
            "asset_id": "a",
            "condition_date": "2026-01-01",
            "condition_status": "UNKNOWN",
            "verification_status": "UNVERIFIED",
            "source_id": "s",
        },
    ]
    r = evaluate(s)
    assert r["current_conditions"][0]["record_id"] == "latest"
    assert r["metrics"]["conditions_coverage"]["value"] == 0.5
    s["assets"][0]["geometry"]["type"] = "Polygon"
    assert evaluate(s)["metrics"]["gis_mapping"]["value"] == 0


def test_three_d_requires_source_placement_and_reviewed_link():
    s = empirical_sample()
    s["model_asset_links"][0]["verification_status"] = "VERIFIED"
    assert evaluate(s)["metrics"]["three_d_coverage"]["value"] == 1
    s["models"][0]["source_id"] = None
    assert evaluate(s)["metrics"]["three_d_coverage"]["value"] == 0
    s["models"][0]["source_id"] = "s"
    s["models"][0]["height"] = None
    assert evaluate(s)["metrics"]["three_d_coverage"]["value"] == 0


def test_conflict_reviews_preserve_values_and_match_ids():
    s = empirical_sample()
    s["scope"]["conflict_reviews"] = [
        {
            "asset_code": "RS-A",
            "attribute_key": "width",
            "record_ids": ["t1", "t2"],
            "status": "RETAIN_BOTH",
            "reviewer": "TEST",
            "rationale": "Different editions",
            "evidence_reference": "TEST",
        }
    ]
    r = evaluate(s)
    assert r["conflicts"][0]["resolution"] == "RETAIN_BOTH"
    assert len(s["records"]["technical"]) == 2
    s["scope"]["conflict_reviews"][0]["record_ids"] = ["wrong"]
    with pytest.raises(ValueError):
        evaluate(s)


def test_task_versions_never_pair_or_pool():
    a = observation("BASELINE", 100)
    b = observation("MVDT", 60)
    b["task_version"] = "TEST-V2"
    summaries, pairs = summarize_retrieval([a, b])
    assert len(summaries) == 2 and len(pairs) == 2
    assert all(
        p["pair_status"] == "UNMATCHED" and p["time_reduction_percent"] is None
        for p in pairs
    )
    b["task_version"] = a["task_version"]
    b["participant_group"] = "RESEARCH_TEAM"
    assert len(summarize_retrieval([a, b])[1]) == 2


def test_timestamp_validation_and_failed_attempt_denominator():
    a = observation("BASELINE", 100)
    a["end_time"] = "2026-10-06T00:00:10+00:00"
    with pytest.raises(ValueError):
        summarize_retrieval([a])
    a = observation("MVDT", 50, "0")
    b = observation("MVDT", 40)
    b["participant_id"] = "P2"
    summaries, _ = summarize_retrieval([a, b])
    assert summaries[0]["attempts"] == 2 and summaries[0]["success_rate"] == 0.5


def test_questionnaires_separate_research_team_and_domain_staff():
    rows = [
        {
            "dataset_version": "TEST",
            "participant_id": "P1",
            "participant_group": group,
            "evidence_reference": "TEST",
            "Q1": score,
        }
        for group, score in [("DOMAIN_STAFF", "5"), ("RESEARCH_TEAM", "1")]
    ]
    results = summarize_usability(rows)
    assert len(results) == 16
    assert {r["mean"] for r in results if r["question"] == "Q1"} == {1, 5}


def test_selected_3d_cannot_skip_picking_acceptance():
    values = inputs()
    values[5][13].update(status="N/A", notes="TEST ONLY")
    report, compiled_scope = compile_scope(*values)
    assert compiled_scope is None
    assert "Core functional acceptance must pass: F14" in report["blockers"]


def test_category_specific_document_na_requires_rationale_and_review():
    values = inputs()
    values[0]["not_applicable"] = {"RS-B": {"document": "TEST reviewed exception"}}
    values[4]["base_scope_sha256"] = base_scope_fingerprint(values[0])
    report, compiled_scope = compile_scope(*values)
    assert report["status"] == "READY_TO_FREEZE"
    validate_scope(compiled_scope)
    compiled_scope["not_applicable"]["RS-B"]["document"] = ""
    with pytest.raises(ValueError, match="rationale"):
        validate_scope(compiled_scope)


def component_fixture():
    values = list(inputs())
    values[0]["component_scope"] = {
        "version": "COMPONENT-SCOPE-v1",
        "primary_sample_count": 2,
        "inventory_evidence": "TEST",
        "technical_evidence": "TEST",
        "components": [
            {
                "asset_code": "RS-CHILD",
                "asset_id": str(uuid4()),
                "parent_asset_code": "RS-A",
                "parent_asset_id": str(uuid4()),
                "technical_record_ids": [str(uuid4())],
            }
        ],
    }
    values[2][0]["related_asset_codes"] += "|RS-CHILD"
    return values


def test_component_scope_does_not_rebind_old_review():
    values = component_fixture()
    assert values[4]["base_scope_sha256"] != base_scope_fingerprint(values[0])
    assert compile_scope(*values)[0]["status"] == "NOT_READY"


def test_component_sources_allowed_without_expanding_primary():
    values = component_fixture()
    values[4]["base_scope_sha256"] = base_scope_fingerprint(values[0])
    report, compiled_scope = compile_scope(*values)
    assert report["status"] == "READY_TO_FREEZE"
    assert compiled_scope["target_asset_codes"] == ["RS-A", "RS-B"]
    assert "RS-CHILD" not in compiled_scope["maim_required_by_asset"]
    values[2][0]["related_asset_codes"] += "|RS-UNKNOWN"
    assert (
        "Source references out-of-scope asset" in compile_scope(*values)[0]["blockers"]
    )


@pytest.mark.parametrize("mutation", ["parent", "duplicate", "overlap"])
def test_invalid_component_scope_rejected(mutation):
    values = component_fixture()
    item = values[0]["component_scope"]["components"][0]
    if mutation == "parent":
        item["parent_asset_code"] = "RS-MISSING"
    elif mutation == "duplicate":
        values[0]["component_scope"]["components"].append(deepcopy(item))
    else:
        values[0]["record_ids"]["technical"] = item["technical_record_ids"]
    values[4]["base_scope_sha256"] = base_scope_fingerprint(values[0])
    assert any("Component scope:" in b for b in compile_scope(*values)[0]["blockers"])
