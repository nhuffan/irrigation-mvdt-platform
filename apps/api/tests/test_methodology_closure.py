"""Synthetic scoped approvals; these fixtures are not actual approvals."""

from copy import deepcopy

import pytest
from test_methodology_review import context, fixture

from scripts.methodology_review import (
    REQUIRED_APPROVALS,
    package_fingerprint,
    validate_role_approvals,
)
from scripts.prepare_empirical_scope import (
    base_scope_fingerprint,
    compile_scope,
    validate_compiled_scope,
)


def approvals(fp):
    return {
        "entries": [
            {
                "approval_type": kind,
                "package_fingerprint": fp,
                "scope": scope,
                "reviewer_role": "RESEARCHER"
                if kind == "RESEARCHER_APPROVAL"
                else "DOMAIN_EXPERT",
                "reviewer_name": "SYNTHETIC TEST",
                "reviewed_at": "2026-10-13T00:00:00+00:00",
                "decision": "APPROVED",
                "evidence": "TEST ONLY",
                "limitations_acknowledged": True,
            }
            for kind, scope in sorted(REQUIRED_APPROVALS)
        ]
    }


def test_two_roles_suffice_without_custodian_or_independence():
    assert validate_role_approvals(approvals("test"), "test") == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("reviewer_role", "AI_METHOD_REVIEWER"),
        ("reviewer_role", "CUSTODIAN"),
        ("package_fingerprint", "stale"),
        ("scope", "OTHER"),
        ("reviewer_name", " "),
        ("reviewed_at", "2026-10-13"),
        ("decision", "PENDING"),
        ("evidence", ""),
        ("limitations_acknowledged", False),
    ],
)
def test_invalid_approval_cannot_pass(field, value):
    a = approvals("test")
    a["entries"][0][field] = value
    assert validate_role_approvals(a, "test")


def test_researcher_cannot_replace_domain():
    a = approvals("test")
    a["entries"] = [
        x for x in a["entries"] if x["approval_type"] == "RESEARCHER_APPROVAL"
    ]
    assert any("DOMAIN_REVIEW/MAIM" in e for e in validate_role_approvals(a, "test"))


def test_duplicates_fail():
    a = approvals("test")
    a["entries"].append(deepcopy(a["entries"][0]))
    assert any("duplicate" in e for e in validate_role_approvals(a, "test"))


def scoped_fixture():
    import hashlib

    data, bundle = fixture()
    data[0]["methodology_approval_policy"] = "ROLE_SCOPED-v1"
    data[4]["base_scope_sha256"] = base_scope_fingerprint(data[0])
    bundle["approval_policy"] = "ROLE_SCOPED-v1"
    bundle["closure_inputs"] = {
        name: {
            "content": "test\nsynthetic\n",
            "sha256": hashlib.sha256(b"test\nsynthetic\n").hexdigest(),
        }
        for name in (
            "mc_r_gate_resolution",
            "researcher_methodology_confirmation",
            "maim_closure_review",
            "ai_consistency_review",
        )
    }
    bundle["approval"] = approvals(package_fingerprint(context(data), bundle))
    return data, bundle


def test_scoped_package_replays():
    data, bundle = scoped_fixture()
    report, scope = compile_scope(*data, methodology=bundle)
    assert scope is not None, report
    validate_compiled_scope(scope)


def test_policy_cannot_be_removed_from_bundle():
    data, bundle = scoped_fixture()
    del bundle["approval_policy"]
    report, scope = compile_scope(*data, methodology=bundle)
    assert scope is None
    assert any("policy differs" in e for e in report["blockers"])


def test_closure_tampering_blocks_freeze():
    data, bundle = scoped_fixture()
    bundle["closure_inputs"]["maim_closure_review"]["content"] += "tamper"
    report, scope = compile_scope(*data, methodology=bundle)
    assert scope is None
    assert any("closure checksum" in e for e in report["blockers"])


def test_new_policy_changes_base_fingerprint():
    data, _ = fixture()
    old = base_scope_fingerprint(data[0])
    data[0]["methodology_approval_policy"] = "ROLE_SCOPED-v1"
    assert base_scope_fingerprint(data[0]) != old


def test_eight_policy_confirmation_does_not_approve_entire_package():
    a = approvals("test")
    for entry in a["entries"]:
        if entry["approval_type"] == "RESEARCHER_APPROVAL":
            entry["scope"] = "EIGHT_RESEARCHER_POLICIES"
    errors = validate_role_approvals(a, "test")
    assert errors == [
        "MC-R: required scoped approval pending: RESEARCHER_APPROVAL/METHODOLOGY_PACKAGE"
    ]


def test_candidate_evidence_checksum_is_validated_even_after_new_approval():
    from test_methodology_review import approve

    data, bundle = fixture()
    bundle["candidate_evidence_review"] = {
        "reviews": {
            name: {"content": "changed", "sha256": "stale"}
            for name in (
                "maintenance_2021_2025_review.csv",
                "maintenance_asset_mapping_review.csv",
            )
        }
    }
    approve(data, bundle)
    report, scope = compile_scope(*data, methodology=bundle)
    assert scope is None
    assert any("candidate review checksum mismatch" in e for e in report["blockers"])
