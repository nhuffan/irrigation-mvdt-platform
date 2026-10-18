"""Synthetic quantitative-evidence tests; no empirical participant or new admission."""

import csv
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import test_methodology_completion as completion_fixtures
from test_methodology_completion import csv_file

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from methodology_completion import build_completion, public_json
from methodology_quantitative import (
    build_quantitative,
    compiler_groups,
    dictionary,
    write_quantitative_artifacts,
)


@pytest.fixture
def quantitative_fixture(tmp_path):
    payload, snapshot, api, base, inventory, controlled, root = (
        completion_fixtures.fixture.__wrapped__(tmp_path)
    )
    csv_file(controlled / "source_inventory.csv", inventory)
    technical = api["RS-C"]["technical"][0]
    technical["reviewed_provenance"] = {
        "verification_level": "L2",
        "source_locator": "PDF:p1:table2",
        "source_code": "RS-S",
    }
    snapshot["rows"]["data_sources"][0]["verification_status"] = "UNVERIFIED"
    return payload, snapshot, api, base, inventory, controlled, root


def completion(fixture, report=None):
    return build_completion(*fixture, compiler_report=report)


def q(fixture, report=None):
    return completion(fixture, report)["quantitative"]


def metric(group, ident):
    return next(m for m in group["metrics"] if m["metric_id"] == ident)


def test_scope_aggregates_do_not_add_descendant_fields_or_expand_primary_sample(
    quantitative_fixture,
):
    value = q(quantitative_fixture)
    groups = {r["scope"]: r for r in value["coverage"]["groups"]}
    assert (
        groups["primary"]["asset_count"],
        groups["primary"]["direct_l2"],
        groups["primary"]["descendant_l2"],
    ) == (1, 0, 1)
    assert (groups["component"]["asset_count"], groups["component"]["direct_l2"]) == (
        1,
        1,
    )
    assert groups["all"]["direct_l2"] == 1
    parent = next(a for a in value["coverage"]["assets"] if a["asset_code"] == "RS-P")
    assert (
        metric(parent, "observed_direct_technical")["status"]
        == "DESCENDANTS_REPORTED_SEPARATELY"
    )
    assert metric(parent, "observed_direct_technical")["value"] is None
    assert parent["maim"]["applicable"] is None
    child = next(a for a in value["coverage"]["assets"] if a["asset_code"] == "RS-C")
    assert child["maim"]["proposed"] is None
    assert child["maim"]["present"] is None


def test_registered_inventory_presence_is_distinct_from_both_formal_technical_protocols(
    quantitative_fixture,
):
    groups = {r["scope"]: r for r in q(quantitative_fixture)["coverage"]["groups"]}
    assert metric(groups["all"], "observed_direct_technical")["numerator"] == 1
    legacy = metric(groups["all"], "protocol_5a_technical")
    assert (legacy["numerator"], legacy["denominator"], legacy["value"]) == (0, 0, None)
    stage5b = metric(groups["all"], "protocol_5b_technical")
    assert stage5b["status"] == "PENDING_REVIEW"
    assert stage5b["numerator"] is stage5b["denominator"] is stage5b["value"] is None
    definitions = {d["id"]: d for d in dictionary()}
    assert "VERIFIED assets" in definitions["protocol_5a_technical"]["denominator_rule"]
    assert "exact units" in definitions["protocol_5b_technical"]["definition"]
    assert "STAGE-5B-v1" in definitions["protocol_5b_technical"]["scope_policy"]


def test_source_verification_is_not_record_verification_and_conflict_mapping_pairs_exist(
    quantitative_fixture,
):
    all_group = next(
        g for g in q(quantitative_fixture)["coverage"]["groups"] if g["scope"] == "all"
    )
    assert metric(all_group, "source_traceability")["value"] == 1
    assert metric(all_group, "verified_source_records")["value"] == 0
    assert metric(all_group, "verified_record_ratio")["value"] == 1
    assert metric(all_group, "exact_conflict_rate")["value"] == 0
    assert metric(all_group, "mapping_verification")["value"] == 1


def test_numeric_zero_text_null_and_unit_locator_source_quality_are_counted_without_coercion(
    quantitative_fixture,
):
    field = quantitative_fixture[2]["RS-C"]["technical"][0]
    text = {
        **deepcopy(field),
        "id": "text",
        "attribute_key": "material",
        "value_number": None,
        "value_text": "Reinforced concrete",
        "unit": "text",
    }
    empty = {
        **deepcopy(field),
        "id": "empty",
        "attribute_key": "unknown",
        "value_number": None,
        "value_text": " ",
        "unit": None,
        "source_id": None,
        "reviewed_provenance": None,
    }
    quantitative_fixture[2]["RS-C"]["technical"] += [text, empty]
    stats = q(quantitative_fixture)["field_quality"]
    assert (
        stats["total_fields"],
        stats["numeric_fields"],
        stats["text_fields"],
        stats["missing_value_fields"],
    ) == (3, 1, 1, 1)
    assert (stats["unit_present"], stats["unit_missing"], stats["unit_text"]) == (
        2,
        1,
        1,
    )
    assert (stats["locator_present"], stats["locator_missing"]) == (2, 1)
    assert (stats["source_linked"], stats["source_missing"]) == (2, 1)
    assert {r["value"]: r["count"] for r in stats["semantics"]} == {
        "SOURCE_REPORTED / HISTORICAL_DOCUMENTED": 2,
        "UNREVIEWED_RECORD": 1,
    }
    assert sum(r["total_fields"] for r in stats["by_category"]) == 3


@pytest.mark.parametrize("state,unit", [("UNVERIFIED", "m"), ("VERIFIED", "cm")])
def test_draft_raw_presence_differs_from_verified_exact_unit_support(
    quantitative_fixture, state, unit
):
    csv_file(
        quantitative_fixture[5] / "maim_review.csv",
        [
            {
                "asset_code": "RS-C",
                "category": "CAT",
                "field": "technical",
                "attribute_key": "height",
                "effective_required": "true",
                "disposition": "REQUIRED",
            }
        ],
    )
    field = quantitative_fixture[2]["RS-C"]["technical"][0]
    field.update(verification_status=state, unit=unit)
    full = completion(quantitative_fixture)
    draft = next(
        a
        for a in full["quantitative"]["coverage"]["assets"]
        if a["asset_code"] == "RS-C"
    )["maim"]
    assert draft["proposed"]["present"] == 1
    assert draft["proposed"]["verified_record"] == 0
    assert draft["proposed"]["missing"] == 0
    assert draft["proposed"]["unknown"] == 0
    assert draft["present"] is draft["verified_record"] is None
    old_draft = next(a for a in full["maim"]["rows"] if a["asset_code"] == "RS-C")[
        "proposed"
    ]
    assert (old_draft["available"], old_draft["missing"]) == (0, 1)
    assert "raw" in draft["proposed_semantics"]


def test_draft_not_applicable_has_explicit_scope_reason_without_formal_count(
    quantitative_fixture,
):
    parent = next(
        a
        for a in q(quantitative_fixture)["coverage"]["assets"]
        if a["asset_code"] == "RS-P"
    )
    assert parent["maim"]["not_applicable"] is None
    assert parent["maim"]["proposed"]["not_applicable"] == 1
    assert parent["maim"]["proposed_not_applicable"][0]["field"] == "three_d"
    assert "scope exclusion" in parent["maim"]["proposed_not_applicable"][0]["reason"]


def test_retained_source_pdf_is_linked_without_claiming_an_asset_document_edge(
    quantitative_fixture,
):
    quantitative_fixture[2]["RS-C"]["documents"] = []
    line = q(quantitative_fixture)["lineage"][0]
    assert line["availability"] == "RETAINED_SOURCE_FILE_NO_ASSET_EDGE"
    assert line["retained_document_records"] == 2
    assert line["linked_document_records"] == 0
    assert len(line["documents"]) == 2
    assert line["source_href"] == "/data-sources/s/documents"
    assert line["asset_href"] == "/assets/c#technical"
    assert all(d["href"].startswith("/documents/") for d in line["documents"])
    assert line["field_locators"] == [
        {"attribute_key": "height", "locators": ["PDF:p1:table2"]}
    ]


def test_no_ui_metadata_does_not_assert_no_private_source_original(
    quantitative_fixture,
):
    quantitative_fixture[1]["rows"]["documents"] = []
    quantitative_fixture[2]["RS-C"]["documents"] = []
    line = q(quantitative_fixture)["lineage"][0]
    assert line["availability"] == "NO_UI_DOCUMENT_METADATA"
    assert line["retained_document_records"] == 0
    assert "NO_RETAINED_FILE" not in line["availability"]


def test_linked_metadata_with_missing_bytes_is_not_called_an_available_pdf(
    quantitative_fixture,
):
    quantitative_fixture[1]["storage_sha256"] = {}
    line = q(quantitative_fixture)["lineage"][0]
    assert line["availability"] == "LINKED_METADATA_BYTES_UNAVAILABLE"
    assert line["documents"] == []
    assert line["linked_document_records"] == 1


def test_candidate_registers_publish_only_fixed_classification_aggregates(
    quantitative_fixture,
):
    csv_file(
        quantitative_fixture[5] / "maintenance_asset_mapping_review.csv",
        [
            {
                "decision": "ACCEPT_CANDIDATE",
                "activity": "/Users/person/private original",
                "reviewer": "PRIVATE PERSON",
            },
            {
                "decision": "Private person is owner",
                "activity": "PRIVATE SECRET",
                "reviewer": "PRIVATE PERSON",
            },
        ],
    )
    aggregate = next(
        r
        for r in q(quantitative_fixture)["retained_review_blockers"]
        if r["id"] == "maintenance_mapping"
    )
    assert aggregate["entry_count"] == 2
    assert aggregate["status_counts"] == [
        {"status": "ACCEPT_CANDIDATE", "count": 1},
        {"status": "OTHER_OR_UNCLASSIFIED", "count": 1},
    ]
    raw = public_json(completion(quantitative_fixture))
    assert (
        "PRIVATE PERSON" not in raw
        and "PRIVATE SECRET" not in raw
        and "/Users/" not in raw
    )
    assert "Private person is owner" not in raw


def test_retrieval_is_per_asset_and_absence_or_representative_is_not_task_success(
    quantitative_fixture,
):
    tasks = q(quantitative_fixture)["retrieval_feasibility"]
    assert len(tasks) == 12
    assert all(task["answer_key_status"] == "NOT_PREPARED" for task in tasks)
    assert all(
        "success" not in task and "completion_time" not in task for task in tasks
    )
    parent = {task["task_id"]: task for task in tasks if task["asset_code"] == "RS-P"}
    assert parent["T1"]["evidence_status"] == "ABSENCE_ONLY"
    assert (
        parent["T3"]["evidence_status"] == parent["T5"]["evidence_status"] == "BLOCKED"
    )
    assert parent["T6"]["evidence_status"] == "REPRESENTATIVE_ONLY"
    child = next(
        task
        for task in tasks
        if task["asset_code"] == "RS-C" and task["task_id"] == "T6"
    )
    assert child["evidence_status"] == "ABSENCE_ONLY"
    assert all(
        row["results"] is None and row["status"] == "NOT_COLLECTED"
        for row in q(quantitative_fixture)["empirical_metrics"]
    )


def test_source_date_kind_api_capture_and_approved_asof_are_separate(
    quantitative_fixture,
):
    value = q(quantitative_fixture)
    assert (
        value["temporal_basis"]["snapshot_captured_at"]
        == quantitative_fixture[0]["captured_at"]
    )
    assert value["temporal_basis"]["api_read_at"] is None
    assert value["temporal_basis"]["dataset_as_of"] is None
    assert all(row["age_days"] is None for row in value["source_ages"])
    known = next(
        row for row in value["source_dates"] if row["date_kind"] == "document_date"
    )
    assert known["date_value"] == "2026-01-01"
    assert (
        next(
            row
            for row in value["source_dates"]
            if row["source_code"] == "RS-S" and row["date_kind"] == "source_date"
        )["date_value"]
        is None
    )
    quantitative_fixture[1]["rows"]["data_sources"][0]["source_date"] = "2025"
    quantitative_fixture[3]["as_of_date"] = "2026-01-01"
    assert all(
        row["age_days"] is None for row in q(quantitative_fixture)["source_ages"]
    )


def test_actual_compiler_findings_are_grouped_once_without_a_fixed_71_or_private_text():
    report = {
        "status": "NOT_READY",
        "blockers": [
            "Browser acceptance pending F02",
            "Domain MAIM approval pending",
            "Source evidence /Users/person/private",
            "Protocol study boundary",
        ],
    }
    grouped = compiler_groups(report)
    assert {g["id"]: g["finding_count"] for g in grouped} == {
        "EVIDENCE": 1,
        "DOMAIN_REVIEW": 1,
        "FUNCTIONAL": 1,
        "PROTOCOL": 1,
    }
    assert sum(g["finding_count"] for g in grouped) == 4
    assert "/Users" not in json.dumps(grouped)
    assert all(g["finding_count"] is None for g in compiler_groups(None))


def test_unavailable_api_fails_closed_instead_of_publishing_zero(quantitative_fixture):
    full = completion(quantitative_fixture)
    quantitative_fixture[2]["RS-C"]["technical"] = None
    with pytest.raises(ValueError, match="unavailable; do not substitute zero"):
        build_quantitative(
            quantitative_fixture[0],
            full,
            quantitative_fixture[1],
            quantitative_fixture[2],
            quantitative_fixture[3],
            quantitative_fixture[5],
            quantitative_fixture[6],
        )


def test_exported_metrics_have_definitions_or_explicit_existing_global_result_references(
    quantitative_fixture,
):
    value = q(quantitative_fixture)
    definitions = {row["id"]: row for row in value["metric_dictionary"]}
    result_ids = {
        r["metric_id"]
        for group in value["coverage"]["groups"]
        for r in group["metrics"]
    }
    assert result_ids <= definitions.keys()
    for row in definitions.values():
        assert all(
            row[key]
            for key in [
                "definition",
                "numerator_rule",
                "denominator_rule",
                "missing_rule",
                "na_rule",
                "temporal_basis",
                "scope_policy",
                "basis_docs",
                "result_reference",
            ]
        )
        assert row["id"] in result_ids or row["result_reference"].startswith(
            "completion."
        )


def test_targeted_csv_json_artifacts_preserve_null_counts_and_input_hashes(
    quantitative_fixture, tmp_path
):
    value = q(quantitative_fixture)
    tmp_path = tmp_path / "artifacts"
    write_quantitative_artifacts(value, tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == {
        "maim-coverage.json",
        "maim-coverage.csv",
        "coverage-metrics.json",
        "coverage-metrics.csv",
        "metric-dictionary.json",
        "quantitative-input-hashes.json",
    }
    manifest = json.loads((tmp_path / "quantitative-input-hashes.json").read_text())
    assert manifest["input_hashes"]
    assert all("/" not in key and ":" not in key for key in manifest["input_hashes"])
    assert len(manifest["output_sha256"]) == 5
    with (tmp_path / "maim-coverage.csv").open() as stream:
        exported = list(csv.DictReader(stream))
    assert all(
        row["applicable"] == row["present"] == row["missing"] == "" for row in exported
    )
    assert (
        json.loads((tmp_path / "maim-coverage.json").read_text())["assets"][0]["maim"][
            "applicable"
        ]
        is None
    )
