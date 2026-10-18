"""Synthetic content tests; no real reviewer, participant or empirical result."""

import csv
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from methodology_completion import (
    build_completion,
    digest,
    public_json,
    require_v1_compatible,
    write_completion_artifacts,
)


def csv_file(path, rows):
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def fixture(tmp_path):
    controlled = tmp_path / "controlled"
    controlled.mkdir()
    source = {
        "id": "s",
        "source_code": "RS-S",
        "title": "Source document title",
        "source_type": "TECHNICAL_REPORT",
        "source_date": None,
        "authority_level": None,
        "verification_status": "VERIFIED",
    }
    sources = [
        {"source_code": "RS-S", "file_expected": "true", "source_date": ""},
        {"source_code": "RS-NO-REVIEW", "file_expected": "false", "source_date": ""},
    ]
    no_review = {**source, "id": "s2", "source_code": "RS-NO-REVIEW"}
    technical = {
        "id": "t",
        "asset_id": "c",
        "attribute_label": "Reported height",
        "source_id": "s",
        "source": {"id": "s"},
        "attribute_key": "height",
        "value_number": 0,
        "value_text": None,
        "unit": "m",
        "verification_status": "VERIFIED",
    }

    def asset(ident, code, parent=None):
        return {
            "id": ident,
            "asset_code": code,
            "name": f"Asset {code}",
            "parent_asset_id": parent,
            "category": {"code": "CAT", "name": "Asset category"},
            "data_status": "REGISTERED",
            "geometry": None,
            "location": {
                "location_status": "NO_LOCATION",
                "review_state": "PENDING",
                "evidence_id": None,
                "crs": None,
                "geometry": None,
                "reviewed_at": None,
                "reviewer": "SYNTHETIC PRIVATE PERSON",
            },
        }

    dbdocs = [
        {
            "id": f"d{i}",
            "source_id": "s",
            "original_file_name": "source.pdf",
            "storage_key": f"documents/private{i}",
            "checksum_sha256": "a" * 64,
            "mime_type": "application/pdf",
            "file_size": 99,
            "page_count": 1,
        }
        for i in range(3)
    ]
    apidoc = {k: v for k, v in dbdocs[0].items() if k != "storage_key"}
    model = {
        "id": "m",
        "source_id": "s",
        "model_code": "RS-M",
        "name": "Representative model",
        "format": "GLB",
        "reservoir_id": "reservoir",
        "coordinate_mode": "LOCAL",
        "verification_status": "PARTIALLY_VERIFIED",
        "storage_key": "models/private.glb",
    }
    link = {
        "id": "l",
        "model_id": "m",
        "asset_id": "p",
        "object_key": "representative",
        "verification_status": "VERIFIED",
    }
    parent, child = asset("p", "RS-P"), asset("c", "RS-C", "p")
    api = {
        code: {
            "asset": a,
            "technical": [],
            "documents": [apidoc],
            "timeline": [],
            "model-links": [],
            "current-condition": None,
        }
        for code, a in [("RS-P", parent), ("RS-C", child)]
    }
    api["RS-C"]["technical"] = [technical]
    api["RS-P"]["model-links"] = [link]
    assets = [
        {
            "asset_code": code,
            "asset_id": a["asset"]["id"],
            "scope": "primary" if code == "RS-P" else "component",
            "parent_asset_code": "" if code == "RS-P" else "RS-P",
            "technical_l2": len(a["technical"]),
            "technical_readback": [
                {
                    "id": "t",
                    "source_id": "s",
                    "source_code": "RS-S",
                    "locator": "PDF:p1:table2",
                    "key": "height",
                    "number": 0,
                    "text": None,
                    "unit": "m",
                }
            ]
            if code == "RS-C"
            else [],
            "canonical_geometry_present": 0,
            "verified_om_records": 0,
            "reference_locations": 0,
            "linked_document_records": 1,
        }
        for code, a in api.items()
    ]
    payload = {
        "schema_version": "METHODOLOGY-DASHBOARD-v1",
        "reservoir_id": "reservoir",
        "captured_at": "2026-01-02T03:04:05+00:00",
        "assets": assets,
        "methodology": {
            "fingerprint": "package-hash",
            "status": "NOT_READY",
            "dataset_status": "NOT_FROZEN",
            "unresolved_gate_count": 9,
        },
        "documents": {"reviewed_distinct_sha256": 1},
        "protocol": {
            "tasks": [{"id": f"T{i}", "prompt": f"Task {i}"} for i in range(1, 7)],
            "questionnaire": [f"Q{i}" for i in range(1, 9)],
        },
    }
    snapshot = {
        "rows": {
            "assets": [parent, child],
            "data_sources": [source, no_review],
            "technical": [technical],
            "conditions": [],
            "inspections": [],
            "repairs": [],
            "maintenance": [],
            "models": [model],
            "documents": dbdocs,
        },
        "storage_sha256": {
            dbdocs[0]["storage_key"]: "a" * 64,
            dbdocs[1]["storage_key"]: "a" * 64,
        },
    }
    base = {"record_ids": {"models": ["m"]}}
    csv_file(
        controlled / "target_assets.csv",
        [{"target_asset_code": "RS-P", "in_scope": "true"}],
    )
    csv_file(
        controlled / "maim_requirements.csv",
        [
            {
                "category": "CAT",
                "field": "technical",
                "attribute_key": "height",
                "expected_unit": "m",
            }
        ],
    )
    rules = [
        {
            "asset_code": "RS-P",
            "category": "CAT",
            "field": field,
            "attribute_key": "",
            "effective_required": required,
            "disposition": disposition,
            "reason": "SYNTHETIC PRIVATE REASON",
            "reviewer": "PRIVATE PERSON",
        }
        for field, required, disposition in [
            ("identity", "true", "REQUIRED"),
            ("category", "true", "REQUIRED"),
            ("source", "true", "REQUIRED"),
            ("technical", "false", "OPTIONAL"),
            ("spatial", "true", "PENDING_EVIDENCE"),
            ("three_d", "false", "NOT_APPLICABLE"),
        ]
    ]
    csv_file(controlled / "maim_review.csv", rules)
    csv_file(
        controlled / "source_review.csv",
        [
            {
                "source_code": "RS-S",
                "authority_class": "SUPPORTING",
                "review_status": "REVIEWED",
                "document_date": "2026-01-01",
                "reviewer": "PRIVATE PERSON",
            }
        ],
    )
    csv_file(
        controlled / "readiness_gates.csv",
        [
            {
                "gate_id": ident,
                "gate_name": "PRIVATE PERSON AND RAW CONTENT",
                "category": "METHODOLOGY",
                "required_for_freeze": "true",
                "current_status": status,
                "evidence": "/Users/private/receipt",
                "blocking_reason": "PRIVATE FREE TEXT",
            }
            for ident, status in [
                ("MC_BOUNDARY", "PASS"),
                ("F08", "N/A"),
                ("F02", "FAIL"),
            ]
        ],
    )
    csv_file(
        controlled / "mc_r_gate_resolution.csv",
        [
            {
                "gate_id": "F02",
                "decision_owner": "Private named individual",
                "blocker_group": "F02_F05_EVIDENCE",
            }
        ],
    )
    (controlled / "methodology_review.json").write_text(
        json.dumps({"approval": {"entries": []}})
    )
    return payload, snapshot, api, base, sources, controlled, tmp_path


def complete(fixture, previous=None):
    return build_completion(*fixture, previous=previous)


def metrics(completion):
    return {m["id"]: m for m in completion["metrics"]}


def test_pending_maim_has_null_final_counts_and_no_component_inheritance(fixture):
    result = complete(fixture)
    rows = {r["asset_code"]: r for r in result["maim"]["rows"]}
    assert result["maim"]["approval_status"] == "PENDING_REVIEW"
    for row in rows.values():
        assert all(
            row[field] is None
            for field in (
                "applicable",
                "available",
                "missing",
                "not_applicable",
                "unknown",
            )
        )
    parent = rows["RS-P"]
    assert parent["proposed"]["applicable"] == 4
    assert parent["proposed"]["available"] == 3
    assert parent["proposed"]["missing"] == 1
    assert parent["proposed"]["not_applicable"] == 1
    technical = next(f for f in parent["fields"] if f["field"] == "technical")
    assert technical["requirement"] == "OPTIONAL"
    assert (
        technical["observed"] == "UNKNOWN"
    )  # not zero-direct-L2 interpreted as missing
    assert rows["RS-C"]["proposed"] is None
    assert rows["RS-C"]["fields"] == []


def test_value_zero_available_but_exact_unit_required(fixture):
    controlled = fixture[5]
    csv_file(
        controlled / "maim_review.csv",
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
    result = complete(fixture)
    row = next(r for r in result["maim"]["rows"] if r["asset_code"] == "RS-C")
    assert row["proposed"]["available"] == 1
    fixture[2]["RS-C"]["technical"][0]["unit"] = "cm"
    row = next(
        r for r in complete(fixture)["maim"]["rows"] if r["asset_code"] == "RS-C"
    )
    assert row["proposed"]["available"] == 0
    assert row["proposed"]["missing"] == 1
    assert row["applicable"] is None


def test_source_document_file_edges_and_unknown_authority_have_distinct_denominators(
    fixture,
):
    result = complete(fixture)
    by_id = metrics(result)
    assert (
        by_id["controlled_registered_sources"]["numerator"],
        by_id["controlled_registered_sources"]["denominator"],
    ) == (2, 2)
    assert (
        by_id["expected_sources_retained"]["numerator"],
        by_id["expected_sources_retained"]["denominator"],
    ) == (1, 1)
    assert (
        by_id["document_integrity"]["numerator"],
        by_id["document_integrity"]["denominator"],
    ) == (2, 3)
    assert by_id["distinct_reviewed_pdfs"]["value"] == 1
    assert by_id["asset_document_edges"]["value"] == 2
    assert by_id["source_authority_unknown"]["numerator"] == 1
    assert by_id["source_dates_known"]["numerator"] == 0
    assert by_id["source_review_dates_known"]["numerator"] == 1
    assert all(
        m["captured_at"] == fixture[0]["captured_at"]
        and m["basis"]
        and m["formula"]
        and m["scope"]
        for m in result["metrics"]
    )


def test_no_denominator_is_unknown_not_zero_and_events_are_not_fabricated(fixture):
    fixture[4].clear()
    result = complete(fixture)
    by_id = metrics(result)
    assert by_id["expected_sources_retained"]["denominator"] == 0
    assert by_id["expected_sources_retained"]["value"] is None
    assert by_id["approved_maim"]["numerator"] is None
    assert by_id["verified_primary_om"]["numerator"] == 0
    assert result["baseline_protocol"]["participant_count"] is None
    assert result["baseline_protocol"]["time_results"] is None
    assert result["questionnaire"]["status"] == "NOT_COLLECTED"
    assert result["questionnaire"]["results"] is None
    assert result["questionnaire"]["instrument"] == "CUSTOM_8_ITEM_NOT_SUS"


def test_conflicts_are_exact_groups_and_never_auto_resolved(fixture):
    second = deepcopy(fixture[1]["rows"]["technical"][0])
    second.update(id="t2", value_number=2)
    fixture[1]["rows"]["technical"].append(second)
    result = complete(fixture)
    assert result["source_quality"]["conflicts"] == [
        {
            "asset_code": "RS-C",
            "attribute_key": "height",
            "record_ids": ["t", "t2"],
            "status": "UNRESOLVED",
        }
    ]
    assert metrics(result)["technical_conflict_rate"]["value"] == 1


def test_private_receipts_names_paths_and_gate_free_text_never_enter_public_extension(
    fixture,
):
    raw = public_json(complete(fixture))
    assert "PRIVATE PERSON" not in raw
    assert "PRIVATE FREE TEXT" not in raw
    assert "Private named individual" not in raw
    assert "storage_key" not in raw
    assert "/Users/" not in raw
    readiness = complete(fixture)["readiness"]
    assert readiness["accepted_gate_ids"] == ["MC_BOUNDARY"]
    assert readiness["not_applicable_gate_ids"] == ["F08"]
    assert readiness["unresolved_gate_ids"] == ["F02"]
    assert readiness["groups"][0]["unresolved_gate_count"] == 1
    assert readiness["declared_gates"][2]["decision_owner"] == "UNASSIGNED"


@pytest.mark.parametrize(
    "value",
    [
        "/Users/person/private.pdf",
        "/Volumes/private/x",
        "/private/tmp/x",
        "/home/person/x",
        "https://api.invalid?key=secret",
        "reviewer_name",
    ],
)
def test_public_summary_fails_closed_on_private_metadata(value):
    with pytest.raises(ValueError, match="Private metadata"):
        public_json({"locator": value})


def test_v1_compatibility_catches_missing_fields_same_count_drift_and_wrong_values():
    old = {
        "schema_version": "METHODOLOGY-DASHBOARD-v1",
        "assets": [{"id": "a", "value": 0, "unit": "m"}],
        "protocol": {"results": None},
    }
    new = {
        **deepcopy(old),
        "schema_version": "METHODOLOGY-DASHBOARD-v2",
        "completion": {},
    }
    require_v1_compatible(new, old)
    new["assets"][0]["value"] = 1
    with pytest.raises(ValueError, match="value mismatch"):
        require_v1_compatible(new, old)
    new = {"schema_version": "METHODOLOGY-DASHBOARD-v2", "assets": []}
    with pytest.raises(ValueError):
        require_v1_compatible(new, old)


def test_snapshot_readback_hash_changes_with_same_count_units_locations_models_sources(
    fixture,
):
    before = complete(fixture)["live_readback"]
    fixture[2]["RS-P"]["asset"]["location"]["geometry"] = {
        "type": "Point",
        "coordinates": [100, 10],
    }
    fixture[1]["rows"]["models"][0]["scale"] = 2
    fixture[1]["rows"]["data_sources"][0]["source_date"] = "2026-01-01"
    after = complete(fixture)["live_readback"]
    assert len(before["assets"]) == len(after["assets"])
    assert digest(before) != digest(after)
    assert after["assets"]["RS-P"]["location"]["geometry"]["coordinates"] == [100, 10]
    assert after["models"][0]["scale"] == 2
    assert after["sources"][0]["source_date"] == "2026-01-01"


def test_artifact_changes_do_not_rebind_unchanged_approval_package(fixture, tmp_path):
    first = complete(fixture, previous={"methodology": {"fingerprint": "package-hash"}})
    fixture[0]["captured_at"] = "2026-01-03T00:00:00+00:00"
    second = complete(
        fixture, previous={"methodology": {"fingerprint": "package-hash"}}
    )
    assert (
        first["provenance"]["package_status"]
        == second["provenance"]["package_status"]
        == "UNCHANGED"
    )
    assert (
        first["provenance"]["completion_artifact_sha256"]
        != second["provenance"]["completion_artifact_sha256"]
    )
    assert first["provenance"]["methodology_package_fingerprint"] == "package-hash"
    write_completion_artifacts(second, tmp_path / "audit")
    manifest = json.loads((tmp_path / "audit/metrics-manifest.json").read_text())
    assert manifest["captured_at"] == second["captured_at"]
    assert (tmp_path / "audit/content-matrix.csv").is_file()
    with (tmp_path / "audit/content-matrix.csv").open() as stream:
        matrix = list(csv.DictReader(stream))
    assert len(matrix) == 8
    assert matrix[-2]["content"].endswith("(MC-3)")
    assert matrix[-1]["content"].endswith("(MC-4)")


def test_unpublished_script_bytes_are_hashed_without_claiming_live_github_links(
    fixture,
):
    root = fixture[-1]
    for name in (
        "scripts/export_methodology_dashboard.py",
        "scripts/methodology_completion.py",
        "research/evaluation/protocol.md",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("SYNTHETIC PUBLIC DOCUMENT\n")
    docs = {d["id"]: d for d in complete(fixture)["provenance"]["documents"]}
    assert docs["exporter"]["href"] is None
    assert docs["completion"]["href"] is None
    assert docs["exporter"]["sha256"]
    assert docs["completion"]["status"] == "IMPLEMENTED"
    assert (
        docs["protocol"]["href"]
        == "https://github.com/nhuffan/irrigation-mvdt-platform/blob/main/research/evaluation/protocol.md"
    )


@pytest.mark.parametrize(
    "change",
    [
        "asset_name",
        "category_name",
        "technical_label",
        "canonical_source",
        "nested_source",
        "document_filename",
        "model_name",
        "model_format",
    ],
)
def test_same_count_display_and_source_join_changes_invalidate_completion_readback(
    fixture, change
):
    before = complete(fixture)["live_readback"]
    api, snapshot = fixture[2], fixture[1]
    if change == "asset_name":
        api["RS-C"]["asset"]["name"] = "Changed asset"
    elif change == "category_name":
        api["RS-C"]["asset"]["category"]["name"] = "Changed category"
    elif change == "technical_label":
        api["RS-C"]["technical"][0]["attribute_label"] = "Different field meaning"
    elif change == "canonical_source":
        api["RS-C"]["technical"][0]["source_id"] = "different-source"
    elif change == "nested_source":
        api["RS-C"]["technical"][0]["source"]["id"] = "different-joined-source"
    elif change == "document_filename":
        api["RS-C"]["documents"][0]["original_file_name"] = "changed.pdf"
    elif change == "model_name":
        snapshot["rows"]["models"][0]["name"] = "Changed model"
    elif change == "model_format":
        snapshot["rows"]["models"][0]["format"] = "IFC"
    after = complete(fixture)["live_readback"]
    assert len(before["assets"]) == len(after["assets"])
    assert len(before["models"]) == len(after["models"])
    assert digest(before) != digest(after)


def test_all_visible_research_models_are_observed_even_outside_old_allowlist(fixture):
    before = complete(fixture)["live_readback"]
    model = deepcopy(fixture[1]["rows"]["models"][0])
    model.update(id="new-model", model_code="RS-NEW", source_id=None)
    unrelated = {**model, "id": "other-reservoir", "reservoir_id": "other"}
    development = {**model, "id": "development", "model_code": "DEV-MODEL"}
    fixture[1]["rows"]["models"] += [model, unrelated, development]
    after = complete(fixture)["live_readback"]
    assert len(before["models"]) == 1
    assert {m["id"] for m in after["models"]} == {"m", "new-model"}
    assert digest(before) != digest(after)


def test_pending_evidence_gate_owner_category_is_not_reassigned_to_researcher(fixture):
    csv_file(
        fixture[5] / "mc_r_gate_resolution.csv",
        [
            {
                "gate_id": "F02",
                "decision_owner": "PENDING_EVIDENCE",
                "blocker_group": "F02_F05_EVIDENCE",
            }
        ],
    )
    gate = next(
        g for g in complete(fixture)["readiness"]["declared_gates"] if g["id"] == "F02"
    )
    assert gate["decision_owner"] == "PENDING_EVIDENCE"
    assert gate["status"] == "FAIL"
    assert gate["blocker_group"] == "F02_F05_EVIDENCE"


@pytest.mark.parametrize(
    "field,new_value",
    [("title", "Different technical source"), ("source_type", "DRAWING")],
)
def test_source_title_or_type_changes_invalidate_same_count_source_readback(
    fixture, field, new_value
):
    before = complete(fixture)["live_readback"]
    fixture[1]["rows"]["data_sources"][0][field] = new_value
    after = complete(fixture)["live_readback"]
    assert len(before["sources"]) == len(after["sources"])
    assert digest(before) != digest(after)
