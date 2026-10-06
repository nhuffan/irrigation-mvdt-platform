"""Synthetic test fixtures only; these are never research results."""

from copy import deepcopy
from uuid import uuid4

import pytest

from scripts.evaluate_research_dataset import evaluate
from scripts.export_research_results import summarize_retrieval, summarize_usability
from scripts.research_common import digest, load_snapshot, validate_scope


def scope():
    return {
        "dataset_version": "TEST-ONLY",
        "data_origin": "RESEARCH",
        "reviewed_by": "test fixture",
        "inventory_reference": "test only",
        "as_of_date": "2026-10-06",
        "reservoir_ids": [str(uuid4())],
        "target_asset_codes": ["RS-A", "RS-B"],
        "source_codes": ["RS-S"],
        "expected_document_source_codes": ["RS-S"],
        "three_d_asset_codes": ["RS-A"],
        "maim_required": ["identity", "technical", "repair"],
        "not_applicable": {"RS-A": {"repair": "No repair expected in this test scope"}},
        "record_ids": {
            k: []
            for k in [
                "technical",
                "conditions",
                "inspections",
                "repairs",
                "maintenance",
                "documents",
                "models",
                "model_asset_links",
            ]
        },
    }


def sample():
    return {
        "scope": scope(),
        "assets": [
            {
                "id": "a",
                "asset_code": "RS-A",
                "name": "A",
                "data_status": "VERIFIED",
                "usable_geometry": True,
                "category_id": "c",
            }
        ],
        "sources": [
            {
                "id": "s",
                "source_code": "RS-S",
                "verification_status": "VERIFIED",
                "source_date": None,
            }
        ],
        "records": {
            "technical": [
                {
                    "id": "t1",
                    "asset_id": "a",
                    "attribute_key": "width",
                    "value_number": 0,
                    "value_text": None,
                    "unit": "m",
                    "verification_status": "VERIFIED",
                    "source_id": "s",
                },
                {
                    "id": "t2",
                    "asset_id": "a",
                    "attribute_key": "width",
                    "value_number": 2,
                    "value_text": None,
                    "unit": "m",
                    "verification_status": "UNVERIFIED",
                    "source_id": None,
                },
            ],
            "conditions": [],
            "inspections": [],
            "repairs": [],
            "maintenance": [],
        },
        "documents": [
            {
                "source_id": "s",
                "file_evidence": {"accessible": True, "checksum_matches": False},
            }
        ],
        "models": [
            {
                "id": "m",
                "file_evidence": {
                    "object_keys": ["gate", "unlinked"],
                    "ambiguous_object_keys": [],
                },
            }
        ],
        "model_asset_links": [
            {
                "model_id": "m",
                "asset_id": "a",
                "object_key": "gate",
                "verification_status": "UNVERIFIED",
            }
        ],
    }


def test_known_metrics_zero_missing_and_conflict():
    result = evaluate(sample())
    m = result["metrics"]
    assert m["asset_identification"]["value"] == 0.5
    assert m["technical_coverage"]["value"] == 1
    assert m["source_traceability"]["value"] == 0.5
    assert m["document_coverage"]["value"] == 1
    assert m["document_integrity"]["value"] == 0
    assert m["three_d_coverage"]["value"] == 1
    assert m["mapping_verification"]["value"] == 0
    assert m["technical_conflict_rate"]["value"] == 1
    assert result["completeness"][0]["value"] == 1
    assert result["completeness"][1]["value"] == 0
    assert result["unlinked_objects"] == [{"model_id": "m", "object_key": "unlinked"}]


def test_empty_denominators_are_null_not_zero():
    s = sample()
    s["assets"] = []
    s["records"] = {k: [] for k in s["records"]}
    s["documents"] = []
    s["models"] = []
    s["model_asset_links"] = []
    s["scope"]["three_d_asset_codes"] = []
    s["scope"]["expected_document_source_codes"] = []
    m = evaluate(s)["metrics"]
    assert m["asset_identification"]["value"] == 0
    for k in [
        "technical_coverage",
        "source_traceability",
        "document_coverage",
        "three_d_coverage",
        "mapping_verification",
    ]:
        assert m[k]["value"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.update(target_asset_codes=[]),
        lambda s: s.update(reviewed_by=""),
        lambda s: s.update(target_asset_codes=["DEV-A"]),
        lambda s: s.update(expected_document_source_codes=["RS-OTHER"]),
        lambda s: s.update(three_d_asset_codes=["RS-OTHER"]),
        lambda s: s.update(maim_required=["made_up"]),
    ],
)
def test_scope_rejects_unapproved_and_synthetic(mutation):
    s = scope()
    mutation(s)
    with pytest.raises(ValueError):
        validate_scope(s)


def test_snapshot_tampering(tmp_path):
    import json

    s = sample()
    p = tmp_path / "snapshot.json"
    p.write_text(json.dumps({"snapshot": s, "sha256": digest(s)}))
    assert load_snapshot(p)[1] == digest(s)
    bad = deepcopy(s)
    bad["scope"]["reviewed_by"] = "changed"
    p.write_text(json.dumps({"snapshot": bad, "sha256": digest(s)}))
    with pytest.raises(ValueError):
        load_snapshot(p)


def observation(workflow, time, success="1"):
    return {
        "dataset_version": "TEST",
        "participant_id": "P1",
        "task_id": "T1",
        "workflow": workflow,
        "completion_time_seconds": str(time),
        "success": success,
        "evidence_reference": "test only",
        "baseline_method": "test folders",
    }


def test_retrieval_pairs_and_failures():
    rows = [observation("BASELINE", 100), observation("MVDT", 60)]
    summaries, pairs = summarize_retrieval(rows)
    assert pairs[0]["time_reduction_percent"] == 40
    assert summaries[0]["success_rate"] == 1
    rows[1]["success"] = "0"
    summaries, pairs = summarize_retrieval(rows)
    assert pairs[0]["time_reduction_percent"] is None
    assert summaries[1]["successful_time_median"] is None
    assert summarize_retrieval([]) == ([], [])
    with pytest.raises(ValueError):
        summarize_retrieval([rows[0], rows[0]])


@pytest.mark.parametrize("value", ["nan", "inf", "-1"])
def test_invalid_elapsed_times(value):
    with pytest.raises(ValueError):
        summarize_retrieval([observation("BASELINE", value)])


def test_questionnaire_missing_and_sample_size():
    r = {
        "dataset_version": "TEST",
        "participant_id": "P1",
        "evidence_reference": "test",
        "Q1": "5",
        "Q2": "NA",
    }
    result = summarize_usability([r])
    assert result[0]["mean"] == 5 and result[0]["sample_std_dev"] is None
    assert len(result) == 1
    with pytest.raises(ValueError):
        summarize_usability([r, r])
    r["Q1"] = "6"
    with pytest.raises(ValueError):
        summarize_usability([r])


def test_freeze_capture_excludes_unlisted_records(domain, tmp_path):
    from app.models.data_source import DataSource
    from app.models.inspection import Inspection
    from app.storage.local import LocalStorage
    from scripts.freeze_research_dataset import capture

    _client, db, reservoir, _empty, _category, assets = domain
    a = assets[0]
    a.asset_code = "RS-A"
    a.data_status = "VERIFIED"
    source = DataSource(
        reservoir_id=reservoir.id,
        source_code="RS-S",
        source_type="OTHER",
        title="TEST ONLY",
    )
    db.add(source)
    db.flush()
    record = Inspection(
        asset_id=a.id,
        source_id=source.id,
        inspection_date=__import__("datetime").date(2025, 1, 1),
    )
    db.add(record)
    db.flush()
    s = scope()
    s["reservoir_ids"] = [str(reservoir.id)]
    snapshot, blobs = capture(db, s, LocalStorage(tmp_path))
    assert (
        len(snapshot["assets"]) == 1
        and snapshot["records"]["inspections"] == []
        and blobs == {}
    )
    s["record_ids"]["inspections"] = [str(record.id)]
    snapshot, _ = capture(db, s, LocalStorage(tmp_path))
    assert len(snapshot["records"]["inspections"]) == 1
    digest(snapshot)
    s["record_ids"]["inspections"] = [str(uuid4())]
    with pytest.raises(ValueError):
        capture(db, s, LocalStorage(tmp_path))


def test_research_import_idempotent_and_no_overwrite(domain):
    from scripts.import_research_data import import_batch

    _client, db, reservoir, *_ = domain
    batch = {
        "data_origin": "RESEARCH",
        "import_batch": "TEST",
        "reviewed_by": "test",
        "source_reference": "test",
        "records": {
            "data_sources": [
                {
                    "id": str(uuid4()),
                    "reservoir_id": str(reservoir.id),
                    "source_code": "RS-TEST",
                    "source_type": "OTHER",
                    "title": "TEST ONLY",
                    "verification_status": "UNVERIFIED",
                }
            ]
        },
    }
    assert import_batch(db, batch)[0]["status"] == "STAGED"
    assert import_batch(db, batch)[0]["status"] == "UNCHANGED"
    batch["records"]["data_sources"][0]["title"] = "CHANGED"
    with pytest.raises(ValueError):
        import_batch(db, batch)


def test_geometry_import_roundtrip(domain):
    from sqlalchemy import func, select

    from app.models.asset import Asset
    from scripts.import_research_data import import_batch

    _client, db, reservoir, _empty, category, _assets = domain
    asset_id = uuid4()
    batch = {
        "data_origin": "RESEARCH",
        "import_batch": "TEST",
        "reviewed_by": "test",
        "source_reference": "test",
        "records": {
            "assets": [
                {
                    "id": str(asset_id),
                    "reservoir_id": str(reservoir.id),
                    "category_id": str(category.id),
                    "asset_code": "RS-SPATIAL",
                    "name": "TEST ONLY",
                    "data_status": "PARTIAL",
                    "geometry": {"type": "Point", "coordinates": [106, 11]},
                }
            ]
        },
    }
    assert import_batch(db, batch)[0]["status"] == "STAGED"
    assert import_batch(db, batch)[0]["status"] == "UNCHANGED"
    assert (
        db.scalar(select(func.ST_X(Asset.geometry)).where(Asset.id == asset_id)) == 106
    )


def test_snapshot_export_cli_is_reproducible(tmp_path, monkeypatch):
    import json
    import sys

    from scripts.evaluate_research_dataset import main

    s = sample()
    s["documents"] = []
    # Model bytes unavailable in this synthetic fixture: no unvalidated links count.
    s["models"][0]["file_evidence"] = {"accessible": False}
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps({"snapshot": s, "sha256": digest(s)}))
    for name in ["one", "two"]:
        monkeypatch.setattr(
            sys,
            "argv",
            ["evaluate", "--snapshot", str(path), "--output", str(tmp_path / name)],
        )
        main()
    assert (tmp_path / "one/evaluation_results.json").read_bytes() == (
        tmp_path / "two/evaluation_results.json"
    ).read_bytes()
    for table in [
        "data_quality",
        "asset_inventory",
        "data_sources",
        "completeness",
        "om_coverage",
        "document_coverage",
        "model_link_coverage",
    ]:
        assert (tmp_path / "one" / f"{table}.csv").exists()


def test_blob_inventory_uses_active_scene_and_detects_duplicate_names(tmp_path):
    from app.models.media import Model
    from app.storage.local import LocalStorage
    from scripts.freeze_research_dataset import file_evidence
    from scripts.seed_media import demo_glb

    storage = LocalStorage(tmp_path)
    storage.store("test.glb", demo_glb())
    model = Model(storage_key="test.glb", format="GLB")
    blobs = {}
    e = file_evidence(model, storage, blobs)
    assert e["accessible"] and len(e["object_keys"]) == 4 and e["sha256"] in blobs
    assert e["ambiguous_object_keys"] == [] and e["unnamed_mesh_nodes"] == []
    storage.store("invalid.glb", b"invalid")
    model.storage_key = "invalid.glb"
    assert (
        file_evidence(model, storage, {})["object_inventory_status"]
        == "UNSUPPORTED_OR_INVALID"
    )
