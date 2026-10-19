"""Synthetic response declarations only; no real reviewer or controlled decisions."""

import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_research_decisions import (
    REQUIRED_INPUTS,
    RESPONSE_FIELDS,
    WORKSHEETS,
    binding_manifest,
    csv_rows,
    private_output,
    validate_return,
)

PACKAGE, BASE = "a" * 64, "b" * 64


def write(path, rows, headers=None):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def bound(tmp_path):
    inputs = []
    for name in REQUIRED_INPUTS:
        path = tmp_path / name
        path.write_text("SYNTHETIC CONTROLLED INPUT\n")
        inputs.append(path)
    context = {
        "methodology_package_sha256": PACKAGE,
        "base_scope_sha256": BASE,
        "controlled_inputs_before": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs
        },
    }
    for filename, (id_column, role, scopes) in WORKSHEETS.items():
        row = {
            id_column: "SYNTHETIC-001",
            "source_id": "source-1",
            "source_locator": "PDF:p3:table2",
            "authority_current": "UNKNOWN_AUTHORITY",
            "number_value": "0",
            "proposed_disposition": "PENDING",
            "unresolved": "true",
            "required_reviewer_role": role,
            "decision_scope": min(scopes),
            "current_package_fingerprint": PACKAGE,
            "current_base_fingerprint": BASE,
            "allowed_response_options": "YES|MODIFY|PENDING",
            **{key: "" for key in RESPONSE_FIELDS},
        }
        write(tmp_path / filename, [row])
    binding = binding_manifest(tmp_path, inputs, PACKAGE, BASE, context)
    return tmp_path, binding, inputs, context


def returned(bound, worksheet="researcher_decision_worksheet.csv", change=None):
    root, _, _, _ = bound
    headers, rows = csv_rows(root / worksheet)
    if change:
        change(rows)
    path = root / "returned.csv"
    write(path, rows, headers)
    return path


def response(row, choice="YES", role="RESEARCHER"):
    row.update(
        human_response=choice,
        response_rationale="Synthetic rationale only",
        reviewer_role=role,
        reviewer_name="SYNTHETIC REVIEWER",
        reviewed_at="2026-10-19T01:02:03+07:00",
        response_evidence="SYNTHETIC RECEIPT:row1",
    )


def test_blank_valid_sheet_remains_awaiting_without_approvals_or_writes(bound):
    result = validate_return(
        bound[1], "researcher_decision_worksheet.csv", returned(bound)
    )
    assert result["status"] == "AWAITING_HUMAN_DECISION"
    assert result["actual_response_count"] == 0
    assert result["approval_entries_generated"] == result["resolved_gate_ids"] == []
    assert result["controlled_files_written"] is False
    assert result["input_sha256_before"] == result["input_sha256_after"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", "other"),
        ("source_locator", "PDF:p4"),
        ("authority_current", "AUTHORITATIVE"),
        ("number_value", ""),
        ("current_package_fingerprint", "c" * 64),
        ("decision_scope", "METHODOLOGY_PACKAGE"),
    ],
)
def test_same_count_identity_source_locator_hash_or_zero_edits_are_rejected(
    bound, field, value
):
    result = validate_return(
        bound[1],
        "researcher_decision_worksheet.csv",
        returned(bound, change=lambda rows: rows[0].update({field: value})),
    )
    assert result["status"] == "INVALID_RETURN"
    assert result["actual_response_count"] == 0


@pytest.mark.parametrize("choice", ["APPROVED", "N/A", "true", "yes"])
def test_unsupported_choice_never_becomes_an_approval(bound, choice):
    path = returned(bound, change=lambda rows: response(rows[0], choice))
    result = validate_return(bound[1], "researcher_decision_worksheet.csv", path)
    assert result["status"] == "INVALID_RETURN"
    assert result["approval_entries_generated"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("reviewer_role", "DOMAIN_EXPERT"),
        ("reviewer_name", " "),
        ("response_evidence", ""),
        ("reviewed_at", "2026-10-19"),
        ("reviewed_at", "2026-10-19T01:02:03"),
    ],
)
def test_actual_choice_requires_explicit_matching_role_name_evidence_and_zoned_time(
    bound, field, value
):
    def change(rows):
        response(rows[0])
        rows[0][field] = value

    result = validate_return(
        bound[1], "researcher_decision_worksheet.csv", returned(bound, change=change)
    )
    assert result["status"] == "INVALID_RETURN"


def test_researcher_cannot_answer_domain_worksheet_as_domain_review(bound):
    name = "maim_domain_decision_workbook.csv"
    result = validate_return(
        bound[1], name, returned(bound, name, lambda rows: response(rows[0]))
    )
    assert result["status"] == "INVALID_RETURN"


def test_yes_to_pending_proposal_records_declaration_but_resolves_no_gate(bound):
    result = validate_return(
        bound[1],
        "researcher_decision_worksheet.csv",
        returned(bound, change=lambda rows: response(rows[0])),
    )
    assert (
        result["status"] == "VALIDATED_RESPONSES_REQUIRES_CONTENT_AND_AUTHORITY_REVIEW"
    )
    assert result["actual_response_count"] == 1
    assert result["accepted_responses"][0]["proposal_disposition"] == "PENDING"
    assert result["accepted_responses"][0]["proposal_unresolved"] == "true"
    assert result["resolved_gate_ids"] == result["approval_entries_generated"] == []


@pytest.mark.parametrize(
    "modified", ["", "change the field", '{"requested_change":"synthetic"}']
)
def test_modify_requires_structured_change_and_precise_source_evidence(bound, modified):
    def change(rows):
        response(rows[0], "MODIFY")
        rows[0]["modified_option"] = modified

    assert (
        validate_return(
            bound[1],
            "researcher_decision_worksheet.csv",
            returned(bound, change=change),
        )["status"]
        == "INVALID_RETURN"
    )


def test_structured_modify_preserves_diff_without_applying_it(bound):
    def change(rows):
        response(rows[0], "MODIFY")
        rows[0]["modified_option"] = json.dumps(
            {
                "requested_change": "Synthetic change",
                "source_evidence": [{"reference": "SYNTHETIC", "locator": "p3"}],
            }
        )

    result = validate_return(
        bound[1], "researcher_decision_worksheet.csv", returned(bound, change=change)
    )
    assert result["actual_response_count"] == 1 and result["response_diff"]
    assert result["controlled_files_written"] is False


def test_duplicate_missing_and_unknown_ids_fail_exact_coverage(bound):
    name = "researcher_decision_worksheet.csv"
    with pytest.raises(ValueError, match="duplicate"):
        validate_return(
            bound[1],
            name,
            returned(bound, change=lambda rows: rows.append(dict(rows[0]))),
        )
    result = validate_return(
        bound[1],
        name,
        returned(bound, change=lambda rows: rows[0].update(question_id="UNKNOWN")),
    )
    assert result["status"] == "INVALID_RETURN"


def test_duplicate_headers_and_malformed_row_width_are_rejected(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("id,id\na,b\n")
    with pytest.raises(ValueError, match="duplicate"):
        csv_rows(path)
    path.write_text("id,name\na,b,extra\n")
    with pytest.raises(ValueError, match="width"):
        csv_rows(path)


def test_incomplete_or_stale_binding_cannot_declare_current_inputs(bound):
    root, _, inputs, context = bound
    with pytest.raises(ValueError, match="complete"):
        binding_manifest(root, [], PACKAGE, BASE, context)
    context["methodology_package_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="Fingerprints"):
        binding_manifest(root, inputs, PACKAGE, BASE, context)


def test_controlled_or_template_byte_drift_invalidates_responses(bound):
    root, binding, inputs, _ = bound
    path = returned(bound)
    inputs[0].write_text("changed controlled input")
    assert (
        validate_return(binding, "researcher_decision_worksheet.csv", path)["status"]
        == "INVALID_RETURN"
    )
    (root / "researcher_decision_worksheet.csv").write_text(
        (root / "researcher_decision_worksheet.csv").read_text() + "\n"
    )
    assert (
        validate_return(binding, "researcher_decision_worksheet.csv", path)["status"]
        == "INVALID_RETURN"
    )


def test_original_evidence_must_be_bound_and_hash_matched(bound):
    root, _, inputs, context = bound
    source = root / "original.pdf"
    source.write_bytes(b"SYNTHETIC ORIGINAL")
    name = root / "source_claim_decision_proposals.csv"
    _headers, rows = csv_rows(name)
    rows[0].update(
        retained_path=str(source),
        original_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    write(name, rows)
    with pytest.raises(ValueError, match="original bytes"):
        binding_manifest(root, inputs, PACKAGE, BASE, context)
    manifest = binding_manifest(root, inputs + [source], PACKAGE, BASE, context)
    assert str(source) in manifest["input_sha256"]
    # Binding the correct path is insufficient when the declared digest conflicts.
    rows[0]["original_sha256"] = "0" * 64
    write(name, rows)
    with pytest.raises(ValueError, match="original bytes"):
        binding_manifest(root, inputs + [source], PACKAGE, BASE, context)


def test_output_cannot_write_pii_to_public_results_or_controlled_inputs(tmp_path):
    for part in (
        "research/evaluation/results/paper/response.json",
        "research/dataset/reviewed/response.json",
        "response.json",
    ):
        with pytest.raises(ValueError, match="ignored private"):
            private_output(tmp_path / part, tmp_path)
    path = (
        tmp_path
        / "research/evaluation/evidence/MAIM-GATE-RESOLUTION/decision-workflow/audits/result.json"
    )
    assert private_output(path, tmp_path) == path
