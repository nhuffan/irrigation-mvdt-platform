"""Synthetic governance fixtures; no case-study approval."""

from copy import deepcopy

import pytest
from test_empirical import inputs

from scripts.prepare_empirical_scope import (
    base_scope_fingerprint,
    compile_scope,
    validate_compiled_scope,
)
from scripts.research_common import digest


def reviewed_inputs():
    data = inputs()
    decisions = []
    for check, requirement in [
        ("F02", "Asset GIS and geometry accuracy"),
        ("F05", "Descending O&M timeline"),
    ]:
        row = next(x for x in data[-1] if x["check_id"] == check)
        row.update(status="N/A", function=requirement, notes="TEST controlled absence")
        decisions.append(
            {
                "check_id": check,
                "dataset_version": data[0]["dataset_version"],
                "base_scope_sha256": base_scope_fingerprint(data[0]),
                "scope_input_sha256": digest(
                    {
                        "base_scope_sha256": base_scope_fingerprint(data[0]),
                        "targets": data[1],
                        "sources": data[2],
                        "requirements": data[3],
                    }
                ),
                "original_requirement": requirement,
                "original_status": "FAIL",
                "evidence_review_scope": "TEST bounded corpus with coverage",
                "evidence_found": "false",
                "proposed_applicability": "N/A",
                "decision": "APPROVED_NA",
                "reviewer": "TEST reviewer",
                "reviewed_at": "2026-10-11T00:00:00+00:00",
                "rationale": "TEST authentic evidence does not support this test",
                "protocol_effect": "TEST disclosure",
                "decision_reference": "TEST explicit decision",
                "requires_retest": "true",
                "retest_status": "PASS",
                "retest_evidence_reference": "TEST empty-state rerun",
            }
        )
    return data, decisions


def test_na_without_controlled_review_is_blocked():
    data, _ = reviewed_inputs()
    assert compile_scope(*data)[0]["status"] == "NOT_READY"


def test_approved_review_is_bound_into_scope_and_revalidated():
    data, decisions = reviewed_inputs()
    report, scope = compile_scope(*data, applicability=decisions)
    assert report["status"] == "READY_TO_FREEZE"
    validate_compiled_scope(scope)
    changed = deepcopy(scope)
    changed["empirical_review"]["applicability"][0]["decision"] = "PENDING"
    with pytest.raises(ValueError):
        validate_compiled_scope(changed)


@pytest.mark.parametrize(
    "field,value",
    [
        ("decision", "PENDING"),
        ("base_scope_sha256", "stale"),
        ("dataset_version", "OTHER"),
        ("original_requirement", "weakened wording"),
        ("evidence_found", "true"),
        ("decision_reference", ""),
        ("reviewer", None),
        ("reviewed_at", "2026-10-11"),
        ("retest_status", "NOT_TESTED"),
        ("rationale", ""),
    ],
)
def test_incomplete_or_stale_decision_cannot_bypass_gate(field, value):
    data, decisions = reviewed_inputs()
    decisions[0][field] = value
    assert compile_scope(*data, applicability=decisions)[0]["status"] == "NOT_READY"


def test_duplicate_and_unrelated_exemptions_rejected():
    data, decisions = reviewed_inputs()
    assert (
        compile_scope(*data, applicability=decisions + [decisions[0]])[0]["status"]
        == "NOT_READY"
    )
    decisions[0]["check_id"] = "F09"
    assert compile_scope(*data, applicability=decisions)[0]["status"] == "NOT_READY"


def test_source_change_invalidates_applicability_review():
    data, decisions = reviewed_inputs()
    data[2][0]["title"] = "CHANGED TEST SOURCE"
    assert compile_scope(*data, applicability=decisions)[0]["status"] == "NOT_READY"
