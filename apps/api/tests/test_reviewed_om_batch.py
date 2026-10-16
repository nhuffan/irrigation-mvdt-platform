"""Synthetic compiler cases, not real research evidence."""

from copy import deepcopy
from uuid import uuid4

import pytest

from scripts.prepare_reviewed_om_batch import compile_batch, locator


def inputs(kind="technical"):
    stamp = {"reviewer": "TEST", "reviewed_at": "2026-10-09T00:00:00+00:00"}
    row = {
        "candidate_id": "C1",
        "asset_code": "RS-A",
        "source_code": "RS-S",
        "evidence_id": "E1",
        "source_locator": "PDF:p2:table-1",
        "record_type": "TECHNICAL",
        "candidate_status": "VERIFIED",
        "candidate_field": "width",
        "candidate_label": "Width",
        "candidate_value": "0",
        "candidate_value_type": "number",
        "candidate_unit": "m",
        **stamp,
    }
    attributes = [
        {
            "category_code": "RS-CAT",
            "attribute_key": "width",
            "attribute_label": "Width",
            "expected_unit": "m",
            "required_by_maim": "false",
        }
    ]
    evidence = [
        {
            "evidence_id": "E1",
            "source_code": "RS-S",
            "asset_codes": "RS-A",
            "drive_file_id": "TEST",
            "mime_type": "application/pdf",
            "review_status": "REVIEWED",
            **stamp,
        }
    ]
    sources = [
        {
            "source_code": "RS-S",
            "related_asset_codes": "RS-A",
            "verification_status": "UNVERIFIED",
        }
    ]
    targets = [
        {
            "target_asset_code": "RS-A",
            "in_scope": "true",
            "verification_status": "VERIFIED",
            "category": "RS-CAT",
        }
    ]
    ids = [
        {"record_type": k, "code": c, "uuid": str(uuid4())}
        for k, c in [("assets", "RS-A"), ("data_sources", "RS-S")]
    ]
    return [[row], attributes, evidence, sources, targets, ids, kind, "TEST"]


def test_zero_provenance_stable_identity_and_no_mutation():
    values = inputs()
    before = deepcopy(values)
    batch, provenance, report = compile_batch(*values)
    record = batch["records"]["technical"][0]
    assert record["value_number"] == 0 and record["value_text"] is None
    assert (
        provenance[0]["record_id"] == record["id"]
        and provenance[0]["source_locator"] == "PDF:p2:table-1"
    )
    assert report["imported_count"] == 0 and values == before
    values[0][0]["candidate_value"] = "2"
    assert compile_batch(*values)[0]["records"]["technical"][0]["id"] == record["id"]


@pytest.mark.parametrize(
    "status", ["EXTRACTED", "REVIEW_PENDING", "REJECTED", "NOT_APPLICABLE"]
)
def test_never_infers_verification(status):
    values = inputs()
    values[0][0]["candidate_status"] = status
    batch, _, report = compile_batch(*values)
    assert batch is None and report["status"] == "NO_VERIFIED_CANDIDATES"


@pytest.mark.parametrize(
    "key,value",
    [
        ("candidate_unit", "mm"),
        ("candidate_field", "unknown"),
        ("candidate_value", "NaN"),
        ("candidate_value", "Infinity"),
        ("candidate_value", ""),
        ("candidate_value", "Unknown"),
        ("candidate_value_type", ""),
        ("reviewer", ""),
        ("reviewed_at", "2026-10-09"),
        ("source_locator", "document"),
        ("evidence_id", "UNKNOWN"),
        ("source_code", "DEV-S"),
        ("asset_code", "DEV-A"),
    ],
)
def test_invalid_facts_block_whole_batch(key, value):
    values = inputs()
    bad = deepcopy(values[0][0])
    bad["candidate_id"] = "C2"
    bad[key] = value
    values[0].append(bad)
    batch, provenance, report = compile_batch(*values)
    assert batch is None and not provenance and report["status"] == "NOT_READY"


@pytest.mark.parametrize("typ", ["MONITORING", "MODEL_OUTPUT", "REFERENCE"])
def test_non_om_types_not_imported_even_if_verified(typ):
    values = inputs()
    values[0][0]["record_type"] = typ
    assert compile_batch(*values)[0] is None


def test_conflicts_retained_and_distinct_ids():
    values = inputs()
    other = deepcopy(values[0][0])
    other.update(candidate_id="C2", candidate_value="5")
    values[0].append(other)
    batch, _, report = compile_batch(*values)
    assert len(batch["records"]["technical"]) == 2
    assert len({r["id"] for r in batch["records"]["technical"]}) == 2
    assert len(report["unresolved_conflicts"]) == 1


@pytest.mark.parametrize(
    "kind,typ,payload",
    [
        ("repairs", "REPAIR", '{"repair_description":"Completed repair"}'),
        ("conditions", "CONDITION", '{"condition_status":"Observed defect"}'),
        ("maintenance", "MAINTENANCE", '{"description":"Completed cleaning"}'),
        ("inspections", "INSPECTION", '{"summary":"Inspection performed"}'),
    ],
)
def test_dated_events_require_complete_date_and_basis(kind, typ, payload):
    values = inputs(kind)
    row = values[0][0]
    row.update(
        record_type=typ,
        candidate_date="2025",
        record_payload=payload,
        event_basis="TEST explicit event",
    )
    assert compile_batch(*values)[0] is None
    row["candidate_date"] = "2025-02-03"
    assert compile_batch(*values)[0]["records"][kind]
    row["event_basis"] = ""
    assert compile_batch(*values)[0] is None


@pytest.mark.parametrize(
    "kind,typ",
    [
        ("repairs", "REPAIR"),
        ("conditions", "CONDITION"),
        ("maintenance", "MAINTENANCE"),
        ("inspections", "INSPECTION"),
    ],
)
def test_empty_event_payload_rejected(kind, typ):
    values = inputs(kind)
    values[0][0].update(
        record_type=typ,
        candidate_date="2025-02-03",
        record_payload="{}",
        event_basis="TEST",
    )
    assert compile_batch(*values)[0] is None


def test_literal_placeholder_requires_explicit_rationale():
    values = inputs()
    values[0][0].update(candidate_value_type="text", candidate_value="Unknown")
    assert compile_batch(*values)[0] is None
    values[0][0]["literal_value_reason"] = "TEST literal source response"
    assert (
        compile_batch(*values)[0]["records"]["technical"][0]["value_text"] == "Unknown"
    )


@pytest.mark.parametrize(
    "citation",
    [
        "PDF:p12:table-2",
        "DRAWING:sheet-03:note-7",
        "XLSX:Sheet1!B12:D16",
        'DOCX:section "Equipment"',
    ],
)
def test_exact_locator(citation):
    locator(citation)


@pytest.mark.parametrize(
    "kind,typ,payload",
    [
        ("technical", "TECHNICAL", ""),
        ("conditions", "CONDITION", '{"condition_status":"TEST condition"}'),
        ("inspections", "INSPECTION", '{"summary":"TEST explicit inspection"}'),
        ("repairs", "REPAIR", '{"repair_description":"TEST completed repair"}'),
        ("maintenance", "MAINTENANCE", '{"description":"TEST performed maintenance"}'),
    ],
)
def test_compiled_batch_db_roundtrip_and_retry(domain, kind, typ, payload):
    from uuid import UUID

    from app.models.asset import Asset
    from app.models.data_source import DataSource
    from scripts.import_research_data import import_batch

    client, db, reservoir, _empty, category, _assets = domain
    values = inputs(kind)
    aid, sid = UUID(values[5][0]["uuid"]), UUID(values[5][1]["uuid"])
    # All rows below belong to the fixture rollback transaction.
    db.add(
        Asset(
            id=aid,
            reservoir_id=reservoir.id,
            category_id=category.id,
            asset_code="RS-" + str(aid),
            name="TEST",
            data_status="REGISTERED",
        )
    )
    db.add(
        DataSource(
            id=sid,
            reservoir_id=reservoir.id,
            source_code="RS-" + str(sid),
            source_type="TEST",
            title="TEST",
            verification_status="UNVERIFIED",
        )
    )
    db.flush()
    values[0][0].update(
        record_type=typ,
        candidate_date="2025-02-03",
        record_payload=payload,
        event_basis="TEST performed event",
    )
    batch, _, report = compile_batch(*values)
    assert report["status"] == "READY_TO_IMPORT"
    assert import_batch(db, batch)[0]["status"] == "STAGED"
    assert import_batch(db, batch)[0]["status"] == "UNCHANGED"
    data = client.get(f"/api/v1/assets/{aid}/{kind}").json()
    assert len(data) == 1 and data[0]["verification_status"] == "VERIFIED"
    current = client.get(f"/api/v1/assets/{aid}/current-condition").json()
    assert (current is not None) == (kind == "conditions")
    timeline = client.get(f"/api/v1/assets/{aid}/timeline").json()
    assert len(timeline) == (0 if kind == "technical" else 1)
    # A changed candidate retains its ID and cannot silently overwrite the DB row.
    record = batch["records"][kind][0]
    record["value_number" if kind == "technical" else "verification_status"] = (
        5 if kind == "technical" else "PARTIALLY_VERIFIED"
    )
    with pytest.raises(ValueError, match="Existing record differs"):
        import_batch(db, batch)


@pytest.mark.parametrize(
    "field,value",
    [
        ("temporal_precision", "YEAR_ONLY"),
        ("temporal_precision", "DATE_RANGE"),
        ("temporal_precision", "UNKNOWN"),
        ("completion_status", "UNVERIFIED"),
        ("completion_status", "PLANNED"),
        ("source_eligibility", "REFERENCE_ONLY"),
        ("mapping_verified", "false"),
    ],
)
def test_declared_annual_candidate_limits_block_even_with_formatted_date(field, value):
    values = inputs("maintenance")
    row = values[0][0]
    row.update(
        record_type="MAINTENANCE",
        candidate_date="2025-01-01",
        record_payload='{"description":"SYNTHETIC TEST ONLY"}',
        event_basis="TEST",
        temporal_precision="FULL_DATE",
        completion_status="VERIFIED",
        source_eligibility="VERIFIED_EVENT",
        mapping_verified="true",
    )
    row[field] = value
    batch, _, report = compile_batch(*values)
    assert batch is None
    assert report["missing_required_fields"]


def test_verified_explicit_event_review_remains_supported():
    values = inputs("maintenance")
    values[0][0].update(
        record_type="MAINTENANCE",
        candidate_date="2025-03-17",
        record_payload='{"description":"SYNTHETIC TEST ONLY"}',
        event_basis="TEST",
        temporal_precision="FULL_DATE",
        completion_status="VERIFIED",
        source_eligibility="VERIFIED_EVENT",
        mapping_verified="true",
    )
    batch, _, report = compile_batch(*values)
    assert batch is not None, report


def test_public_pdf_preserves_url_and_hash_without_fake_drive_id():
    args = inputs()
    e = args[2][0]
    e.update(
        drive_file_id="",
        source_url="https://example.org/report.pdf",
        checksum_sha256="a" * 64,
        file_name="report.pdf",
    )
    batch, provenance, _ = compile_batch(*args)
    assert batch is not None
    assert provenance[0]["drive_file_id"] == ""
    assert provenance[0]["checksum_sha256"] == "a" * 64
    assert provenance[0]["source_url"] == e["source_url"]


@pytest.mark.parametrize(
    "change",
    [
        {"checksum_sha256": ""},
        {"checksum_sha256": "not-a-hash"},
        {"source_url": "http://example.org/report.pdf"},
        {"source_url": "https:///report.pdf"},
        {"file_name": ""},
        {"source_url": "https://user:password@example.org/report.pdf"},
    ],
)
def test_public_pdf_requires_exact_file_identity(change):
    args = inputs()
    args[2][0].update(
        drive_file_id="",
        source_url="https://example.org/report.pdf",
        checksum_sha256="a" * 64,
        file_name="report.pdf",
    )
    args[2][0].update(change)
    batch, _, report = compile_batch(*args)
    assert batch is None
    assert report["status"] == "NOT_READY"
