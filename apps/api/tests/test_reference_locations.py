"""Synthetic reference review tests; receipts below are fixtures, never research approval."""

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from pypdf import PdfWriter

from app.core.config import settings
from app.models.asset_technical_attribute import AssetTechnicalAttribute
from app.models.data_source import DataSource
from app.models.media import Document
from app.services.coordinate_input import CoordinateInput, parse_coordinates
from app.services.spatial_candidates import HumanReview, SpatialCandidate
from scripts.reference_locations import (
    apply_candidates,
    atomic_write,
    candidate_digest,
    load_packet,
    merge_candidates,
    preflight,
    read_bundle,
)


def coordinate(x="106.345809", y="11.323019", **kwargs):
    return CoordinateInput(
        source_crs=kwargs.get("source_crs", "EPSG:4326"),
        axis_order=kwargs.get("axis_order", "longitude_latitude"),
        format=kwargs.get("format", "decimal"),
        x=x,
        y=y,
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        (coordinate(), [106.345809, 11.323019]),
        (
            coordinate("11.323019", "106.345809", axis_order="latitude_longitude"),
            [106.345809, 11.323019],
        ),
        (
            coordinate("106°20'44.9124\"E", "11°19'22.8684\"N", format="dms"),
            [106.345809, 11.323019],
        ),
        (
            coordinate("106 20 44.9124 E", "11 19 22.8684 N", format="dms"),
            [106.345809, 11.323019],
        ),
        (
            coordinate("106°20'44.9124\"W", "11°19'22.8684\"S", format="dms"),
            [-106.345809, -11.323019],
        ),
    ],
)
def test_decimal_dms_exact_axes_precision(value, expected):
    result = parse_coordinates(value)
    assert result["geometry"]["coordinates"] == pytest.approx(expected, abs=1e-10)
    assert result["original"] == value.model_dump()
    assert result["input_decimal_places"] == (
        [4, 4] if value.format == "dms" else [6, 6]
    )
    assert "not positional accuracy" in result["precision_note"]


@pytest.mark.parametrize(
    "value",
    [
        coordinate("11", "106"),
        coordinate("NaN", "11"),
        coordinate("106,345", "11"),
        coordinate("Infinity", "11"),
        coordinate("181", "11"),
        coordinate("106", "11", axis_order="easting_northing"),
        coordinate("106", "11", format="utm"),
        coordinate("106°60'0\"E", "11°0'0\"N", format="dms"),
        coordinate("106°0'60\"E", "11°0'0\"N", format="dms"),
        coordinate("106°0'0\"N", "11°0'0\"E", format="dms"),
        coordinate("-106°0'0\"W", "11°0'0\"N", format="dms"),
        coordinate("106°0'0\"E", "90°0'1\"N", format="dms"),
        coordinate("500000", "0", source_crs="EPSG:32648", format="utm"),
        coordinate(
            "1250000",
            "500000",
            source_crs="EPSG:32648",
            format="utm",
            axis_order="easting_northing",
        ),
    ],
)
def test_bad_coordinates_never_infer_axis_or_crs(value):
    with pytest.raises(ValueError):
        parse_coordinates(value)


def test_utm48n_uses_existing_postgis_explicit_axes(domain):
    _, db, *_ = domain
    result = parse_coordinates(
        coordinate(
            "500000",
            "0",
            source_crs="EPSG:32648",
            format="utm",
            axis_order="easting_northing",
        ),
        db,
    )
    assert result["geometry"]["coordinates"] == pytest.approx([105, 0], abs=1e-10)
    assert "ST_Transform" in result["method"]
    with pytest.raises(ValueError):
        CoordinateInput.model_validate(
            {
                "source_crs": "UNKNOWN",
                "axis_order": "longitude_latitude",
                "format": "decimal",
                "x": "106",
                "y": "11",
            }
        )


@pytest.fixture
def reference(domain, tmp_path, monkeypatch):
    client, db, reservoir, _, _, assets = domain
    asset = assets[-1]
    asset.asset_code = "RS-SPATIAL-FIXTURE"
    db.flush()
    original = tmp_path / "original.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(original)
    checksum = hashlib.sha256(original.read_bytes()).hexdigest()
    source = DataSource(
        reservoir_id=reservoir.id,
        source_code=f"RS-SOURCE-{uuid4()}",
        source_type="REPORT",
        title="Synthetic spatial fixture",
    )
    db.add(source)
    db.flush()
    document = Document(
        source_id=source.id,
        document_code=f"RS-DOC-{uuid4()}",
        original_file_name=original.name,
        storage_key=original.name,
        checksum_sha256=checksum,
        file_size=original.stat().st_size,
        mime_type="application/pdf",
        page_count=1,
    )
    db.add(document)
    db.flush()
    monkeypatch.setattr(settings, "storage_root", tmp_path)
    technical = AssetTechnicalAttribute(
        asset_id=asset.id,
        source_id=source.id,
        attribute_key="fixture_spatial_link",
        attribute_label="Synthetic source binding",
        value_text="Fixture only",
        verification_status="PARTIALLY_VERIFIED",
    )
    db.add(technical)
    db.flush()
    from app.schemas.technical_attribute import AssetTechnicalAttributeResponse
    from app.services.reviewed_provenance import BINDING_FIELDS

    record = AssetTechnicalAttributeResponse.model_validate(technical)
    reviewed_path = tmp_path / "provenance.json"
    reviewed_path.write_text(
        json.dumps(
            {
                "version": 1,
                "records": {
                    str(technical.id): {
                        "record": record.model_dump(
                            mode="json", include=set(BINDING_FIELDS)
                        ),
                        "provenance": {
                            "source_code": source.source_code,
                            "verification_level": "L2",
                            "source_locator": "PDF:p1:fixture",
                            "evidence_id": "SYNTHETIC-SPATIAL-FIXTURE",
                            "authority": "Synthetic fixture only",
                            "reviewer": "Fixture reviewer",
                            "reviewed_at": "2026-01-01",
                        },
                    }
                },
            }
        )
    )
    monkeypatch.setattr(settings, "reviewed_provenance_path", reviewed_path)
    candidate = SpatialCandidate(
        candidate_id="fixture-reference",
        asset_id=asset.id,
        reservoir_id=reservoir.id,
        asset_code=asset.asset_code,
        parent_asset_id=asset.parent_asset_id,
        source_label="Fixture feature",
        source="Synthetic spatial source",
        source_id=source.id,
        document_id=document.id,
        source_sha256=checksum,
        original_path=str(original),
        physical_page=1,
        locator="PDF:p1:fixture",
        coordinates=coordinate(),
        coordinate_basis="Explicit WGS84 coordinate table",
        identity_basis="Fixture exact asset label",
        identity_confirmed=True,
        accuracy_limitation="Unknown; reference only",
        next_action="Obtain actual human reference review",
    )
    return client, db, asset, candidate, tmp_path


def approve(candidate, directory, **changes):
    # Synthetic fixture only: production workflow never manufactures a receipt.
    receipt = {
        "decision": "APPROVE_REFERENCE_LOCATION",
        "candidate_sha256": candidate_digest(candidate),
        "reviewer": "SYNTHETIC FIXTURE REVIEWER",
        "reviewer_role": "RESEARCHER",
        "reviewed_at": "2026-01-01T00:00:00Z",
        "reference_only": True,
        "identity_confirmed": True,
        "source_binding_confirmed": False,
        "resolved_conflicts": [],
        "conflict_resolution": None,
        "colocated_with": [],
        "colocation_basis": None,
    } | changes
    path = directory / f"{candidate.candidate_id}-receipt.json"
    path.write_text(json.dumps(receipt))
    candidate.review = HumanReview.model_validate(
        receipt
        | {
            "evidence_path": str(path),
            "evidence_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )


def test_pending_stages_but_never_applies_or_exposes_coordinates(
    reference, monkeypatch
):
    client, db, asset, candidate, path = reference
    candidate.identity_confirmed = False
    candidate.source_id = candidate.document_id = None
    bundle = merge_candidates(db, {"version": 1, "records": {}}, [candidate], {})
    row = preflight(db, [candidate], bundle)[0]
    assert {
        "HUMAN_REFERENCE_REVIEW_REQUIRED",
        "ASSET_IDENTITY_REVIEW_REQUIRED",
        "REGISTERED_SOURCE_DOCUMENT_BINDING_REQUIRED",
    } <= set(row["reasons"])
    with pytest.raises(ValueError, match="blocked"):
        apply_candidates(db, bundle, [candidate], [candidate.candidate_id])
    sidecar = path / "locations.json"
    atomic_write(sidecar, bundle)
    monkeypatch.setattr(settings, "asset_locations_path", sidecar)
    result = client.get(f"/api/v1/assets/{asset.id}")
    assert result.status_code == 200
    location = result.json()["location"]
    assert location["location_status"] == "NO_LOCATION" and location["geometry"] is None
    assert location["spatial_disposition"] == "CANDIDATE_NEEDS_REVIEW"
    summary = location["candidates"][0]
    assert summary["source_crs"] == "EPSG:4326"
    assert not {
        "original_path",
        "coordinates",
        "source_sha256",
        "review",
        "geometry",
    } & set(summary)
    assert "106.345809" not in json.dumps(location)


def test_selective_apply_idempotence_and_no_db_geometry_write(reference):
    _, db, asset, candidate, path = reference
    approve(candidate, path)
    original = {"version": 1, "records": {}}
    merged = merge_candidates(db, original, [candidate], {})
    result, rows = apply_candidates(db, merged, [candidate], [candidate.candidate_id])
    assert rows[0]["status"] == "ELIGIBLE"
    assert result["records"][str(asset.id)]["location_status"] == "REFERENCE_LOCATION"
    assert asset.geometry is None
    repeated, rows = apply_candidates(db, result, [candidate], [candidate.candidate_id])
    assert rows[0]["status"] == "UNCHANGED" and repeated == result
    assert merged["records"] == {} and original["records"] == {}


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("asset_id", uuid4(), "ASSET_IDENTITY_MISMATCH"),
        ("reservoir_id", uuid4(), "ASSET_IDENTITY_MISMATCH"),
        ("asset_code", "RS-OTHER", "ASSET_IDENTITY_MISMATCH"),
        ("parent_asset_id", uuid4(), "ASSET_HIERARCHY_MISMATCH"),
        ("source_id", uuid4(), "SOURCE_IDENTITY_MISMATCH"),
        ("document_id", uuid4(), "DOCUMENT_SOURCE_MISMATCH"),
        ("source_sha256", "0" * 64, "ORIGINAL_CHECKSUM_MISMATCH"),
        ("physical_page", 2, "PHYSICAL_PAGE_OUT_OF_RANGE"),
    ],
)
def test_identity_source_page_checksum_failures(reference, field, value, reason):
    _, db, _, candidate, _ = reference
    setattr(candidate, field, value)
    row = preflight(db, [candidate], {"version": 1, "records": {}})[0]
    assert reason in row["reasons"] and row["status"] == "BLOCKED"


def test_review_reuse_or_changed_original_is_blocked(reference):
    _, db, _, candidate, path = reference
    approve(candidate, path)
    candidate.coordinates.x = "106.345810"
    assert (
        "REVIEW_CANDIDATE_HASH_MISMATCH"
        in preflight(db, [candidate], {"version": 1, "records": {}})[0]["reasons"]
    )
    candidate.coordinates.x = "106.345809"
    receipt = candidate.review.evidence_path
    with open(receipt, "a") as handle:
        handle.write(" ")
    assert (
        "REVIEW_RECEIPT_CHECKSUM_MISMATCH"
        in preflight(db, [candidate], {"version": 1, "records": {}})[0]["reasons"]
    )


def test_future_or_absent_receipt_and_explicit_identity_gate(reference):
    _, db, _, candidate, path = reference
    candidate.identity_confirmed = False
    approve(
        candidate,
        path,
        reviewed_at=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
        identity_confirmed=False,
    )
    row = preflight(db, [candidate], {"version": 1, "records": {}})[0]
    assert {"ASSET_IDENTITY_REVIEW_REQUIRED", "REVIEW_DATE_IN_FUTURE"} <= set(
        row["reasons"]
    )
    candidate.review.evidence_path = str(path / "missing.json")
    assert (
        "REVIEW_RECEIPT_UNAVAILABLE"
        in preflight(db, [candidate], {"version": 1, "records": {}})[0]["reasons"]
    )


def test_existing_approved_point_never_overwritten(reference):
    _, db, asset, candidate, path = reference
    approve(candidate, path)
    initial, _ = apply_candidates(
        db, {"version": 1, "records": {}}, [candidate], [candidate.candidate_id]
    )
    preserved = deepcopy(initial["records"])
    candidate.coordinates.x = "106.4"
    approve(candidate, path)
    row = preflight(db, [candidate], initial)[0]
    assert any(
        reason.startswith("EXISTING_REFERENCE_PROTECTED") for reason in row["reasons"]
    )
    with pytest.raises(ValueError):
        apply_candidates(db, initial, [candidate], [candidate.candidate_id])
    assert initial["records"] == preserved
    assert asset.geometry is None


def test_duplicate_culvert_and_contradiction_detection(reference):
    _, db, _, candidate, path = reference
    other = candidate.model_copy(
        deep=True, update={"candidate_id": "other-culvert", "asset_id": uuid4()}
    )
    approve(candidate, path)
    rows = preflight(db, [candidate, other], {"version": 1, "records": {}})
    assert "DUPLICATE_SOURCE_COORDINATE:other-culvert" in rows[0]["issues"]
    assert "COLOCATION_REVIEW_REQUIRED" in rows[0]["reasons"]
    alternate = candidate.model_copy(
        deep=True, update={"candidate_id": "alternate-report"}
    )
    alternate.coordinates.x = "106.35"
    assert (
        "CONTRADICTORY_COORDINATE:alternate-report"
        in preflight(db, [candidate, alternate], {"version": 1, "records": {}})[0][
            "issues"
        ]
    )


def test_pending_candidate_revision_is_immutable_but_actual_receipt_can_be_attached(
    reference,
):
    _, db, _, candidate, path = reference
    original = merge_candidates(db, {"version": 1, "records": {}}, [candidate], {})
    approve(candidate, path)
    reviewed = merge_candidates(db, original, [candidate], {})
    assert reviewed["candidates"][0]["review"] is not None
    assert merge_candidates(db, reviewed, [candidate], {}) == reviewed
    candidate.locator = "different physical feature"
    with pytest.raises(ValueError, match="revision"):
        merge_candidates(db, original, [candidate], {})


def test_dispositions_validate_exact_asset_and_candidate_bindings(reference):
    _, db, asset, candidate, path = reference
    packet = {
        "version": 1,
        "candidates": [candidate.model_dump(mode="json")],
        "dispositions": {
            str(asset.id): {
                "asset_id": str(asset.id),
                "reservoir_id": str(asset.reservoir_id),
                "asset_code": asset.asset_code,
                "status": "CONFLICTED",
                "reason": "Duplicated source coordinate",
                "next_action": "Review labelled original",
                "candidate_ids": ["unknown"],
            }
        },
    }
    file = path / "packet.json"
    file.write_text(json.dumps(packet))
    candidates, dispositions = load_packet(file)
    with pytest.raises(ValueError, match="exact asset"):
        merge_candidates(db, {"version": 1, "records": {}}, candidates, dispositions)
    packet["dispositions"][str(asset.id)]["candidate_ids"] = [candidate.candidate_id]
    file.write_text(json.dumps(packet))
    candidates, dispositions = load_packet(file)
    staged = merge_candidates(
        db, {"version": 1, "records": {}}, candidates, dispositions
    )
    atomic_write(file, staged)
    assert read_bundle(file) == staged
    assert staged["records"] == {}


def test_dms_negative_zero_preserves_southern_axis_sign():
    value = coordinate("106 0 0", "-0 30 0", format="dms")
    assert parse_coordinates(value)["geometry"]["coordinates"] == [106, -0.5]


def test_corrupt_pdf_is_a_structured_preflight_blocker(reference):
    _, db, _, candidate, path = reference
    original = path / "corrupt.pdf"
    original.write_bytes(b"not a PDF")
    candidate.original_path = str(original)
    candidate.source_sha256 = hashlib.sha256(original.read_bytes()).hexdigest()
    candidate.source_id = candidate.document_id = None
    assert (
        "SOURCE_ORIGINAL_UNREADABLE"
        in preflight(db, [candidate], {"version": 1, "records": {}})[0]["reasons"]
    )


def test_preflight_packet_reports_invalid_identity_without_staging(reference):
    _, db, _, candidate, _ = reference
    candidate.asset_id = uuid4()
    merged = merge_candidates(
        db, {"version": 1, "records": {}}, [candidate], {}, validate_sources=False
    )
    assert "ASSET_IDENTITY_MISMATCH" in preflight(db, [candidate], merged)[0]["reasons"]
    assert merged["records"] == {}


def test_existing_duplicate_candidate_ids_cannot_be_silently_dropped(reference):
    _, _, _, candidate, path = reference
    sidecar = path / "duplicate.json"
    sidecar.write_text(
        json.dumps(
            {
                "version": 1,
                "records": {},
                "candidates": [candidate.model_dump(mode="json")] * 2,
            }
        )
    )
    with pytest.raises(ValueError, match="Duplicate existing candidate IDs"):
        read_bundle(sidecar)


@pytest.mark.parametrize("south", ["0 30 0 S", "0 30 0 s", "0°30'0\"S"])
def test_dms_hemisphere_s_is_never_consumed_as_seconds_unit(south):
    assert parse_coordinates(coordinate("106 0 0 E", south, format="dms"))["geometry"][
        "coordinates"
    ] == [106, -0.5]


def test_initial_identity_candidate_is_confirmed_only_by_real_pinned_receipt(reference):
    _, db, _, candidate, path = reference
    candidate.identity_confirmed = False
    staged = merge_candidates(db, {"version": 1, "records": {}}, [candidate], {})
    approve(candidate, path)
    reviewed = merge_candidates(db, staged, [candidate], {})
    assert preflight(db, [candidate], reviewed)[0]["status"] == "ELIGIBLE"
    result, _ = apply_candidates(db, reviewed, [candidate], [candidate.candidate_id])
    assert len(result["records"]) == 1


def test_same_reservoir_source_without_exact_reviewed_asset_association_is_blocked(
    reference, monkeypatch
):
    _, db, _, candidate, path = reference
    approve(candidate, path)
    monkeypatch.setattr(
        settings, "reviewed_provenance_path", path / "absent-provenance.json"
    )
    row = preflight(db, [candidate], {"version": 1, "records": {}})[0]
    assert "REVIEWED_EXACT_ASSET_SOURCE_BINDING_REQUIRED" in row["reasons"]


def test_wrong_but_globally_valid_coordinate_requires_site_plausibility_review(
    reference,
):
    _, db, _, candidate, path = reference
    candidate.coordinates.x = "11.3"
    approve(candidate, path)
    row = preflight(db, [candidate], {"version": 1, "records": {}})[0]
    assert "RESERVOIR_CONTEXT_DISTANCE_EXCEEDS_100KM" in row["issues"]
    assert "SOURCE_OR_COORDINATE_CONFLICT_REVIEW_REQUIRED" in row["reasons"]


def test_same_coordinate_different_reference_evidence_is_not_silently_reassigned(
    reference,
):
    _, db, _, candidate, path = reference
    approve(candidate, path)
    initial, _ = apply_candidates(
        db, {"version": 1, "records": {}}, [candidate], [candidate.candidate_id]
    )
    candidate.candidate_id = "same-coordinates-different-source-review"
    approve(candidate, path)
    row = preflight(db, [candidate], initial)[0]
    assert any(
        reason.startswith("EXISTING_REFERENCE_PROTECTED") for reason in row["reasons"]
    )
    assert row["status"] == "BLOCKED"


def test_operator_flags_candidate_disposition_stage_and_repeat_without_manual_json(
    reference, monkeypatch, capsys
):
    from contextlib import nullcontext

    from scripts import reference_locations as operator

    _, db, asset, candidate, path = reference
    monkeypatch.setattr(operator, "SessionLocal", lambda: nullcontext(db))
    packet = path / "operator-packet.json"
    sidecar = path / "operator-sidecar.json"

    def run(*arguments):
        monkeypatch.setattr("sys.argv", ["reference_locations", *map(str, arguments)])
        operator.main()
        return json.loads(capsys.readouterr().out)

    arguments = [
        "add-candidate",
        "--asset",
        asset.id,
        "--candidate-id",
        candidate.candidate_id,
        "--original",
        candidate.original_path,
        "--source-label",
        candidate.source_label,
        "--source-title",
        candidate.source,
        "--source-id",
        candidate.source_id,
        "--document",
        candidate.document_id,
        "--page",
        1,
        "--locator",
        candidate.locator,
        "--basis",
        candidate.coordinate_basis,
        "--identity-basis",
        candidate.identity_basis,
        "--limitation",
        candidate.accuracy_limitation,
        "--next-action",
        candidate.next_action,
        "--source-crs",
        "EPSG:4326",
        "--axis-order",
        "longitude_latitude",
        "--coordinate-format",
        "decimal",
        "--x",
        candidate.coordinates.x,
        "--y",
        candidate.coordinates.y,
        "--output",
        packet,
    ]
    assert run(*arguments)["write_applied"] is False
    assert not packet.exists()
    assert run(*arguments, "--apply")["write_applied"] is True
    assert (
        run(
            "set-disposition",
            "--asset",
            asset.id,
            "--disposition-status",
            "CANDIDATE_NEEDS_REVIEW",
            "--reason",
            "Synthetic fixture awaits actual review",
            "--next-action",
            candidate.next_action,
            "--candidate",
            candidate.candidate_id,
            "--output",
            packet,
            "--apply",
        )["status"]
        == "CANDIDATE_NEEDS_REVIEW"
    )
    dry = run("stage", "--packet", packet, "--sidecar", sidecar)
    assert dry["accepted_before"] == dry["accepted_after"] == 0
    assert not sidecar.exists()
    assert (
        run("stage", "--packet", packet, "--sidecar", sidecar, "--apply")[
            "sidecar_changed"
        ]
        is True
    )
    preserved = sidecar.read_bytes()
    repeated = run("stage", "--packet", packet, "--sidecar", sidecar, "--apply")
    assert repeated["sidecar_changed"] is False and sidecar.read_bytes() == preserved
    staged = SpatialCandidate.model_validate(read_bundle(sidecar)["candidates"][0])
    assert staged.identity_confirmed is False and staged.review is None
    approve(staged, path)
    attached = run(
        "attach-review",
        "--candidate",
        staged.candidate_id,
        "--review-receipt",
        staged.review.evidence_path,
        "--sidecar",
        sidecar,
        "--apply",
    )
    assert (
        attached["sidecar_changed"] is True
        and attached["candidates"][0]["status"] == "ELIGIBLE"
    )
    applied = run(
        "apply", "--candidate", staged.candidate_id, "--sidecar", sidecar, "--apply"
    )
    assert applied["accepted_before"] == 0 and applied["accepted_after"] == 1
    accepted = sidecar.read_bytes()
    repeated = run(
        "apply", "--candidate", staged.candidate_id, "--sidecar", sidecar, "--apply"
    )
    assert repeated["sidecar_changed"] is False and sidecar.read_bytes() == accepted
    assert asset.geometry is None


def test_review_attachment_refuses_wrong_candidate_receipt_without_mutating_sidecar(
    reference, monkeypatch, capsys
):
    from contextlib import nullcontext

    from scripts import reference_locations as operator

    _, db, _, candidate, path = reference
    sidecar = path / "locations.json"
    atomic_write(
        sidecar, merge_candidates(db, {"version": 1, "records": {}}, [candidate], {})
    )
    approve(candidate, path)
    content = json.loads(Path(candidate.review.evidence_path).read_text())
    content["candidate_sha256"] = "0" * 64
    receipt = path / "wrong-review.json"
    receipt.write_text(json.dumps(content))
    before = sidecar.read_bytes()
    monkeypatch.setattr(operator, "SessionLocal", lambda: nullcontext(db))
    monkeypatch.setattr(
        "sys.argv",
        [
            "reference_locations",
            "attach-review",
            "--candidate",
            candidate.candidate_id,
            "--review-receipt",
            str(receipt),
            "--sidecar",
            str(sidecar),
            "--apply",
        ],
    )
    with pytest.raises(SystemExit) as caught:
        operator.main()
    assert caught.value.code == 2
    assert "REVIEW_CANDIDATE_HASH_MISMATCH" in capsys.readouterr().err
    assert sidecar.read_bytes() == before


def test_genuinely_shared_reference_requires_named_colocation_review_and_keeps_exact_points(
    reference,
):
    _, db, asset, candidate, path = reference
    parent = db.get(type(asset), asset.parent_asset_id)
    approved_parent = {
        "asset_id": str(parent.id),
        "reservoir_id": str(parent.reservoir_id),
        "asset_code": parent.asset_code,
        "location_status": "REFERENCE_LOCATION",
        "geometry": {"type": "Point", "coordinates": [106.345809, 11.323019]},
        "crs": "EPSG:4326",
        "source": "Synthetic shared-complex source",
        "locator": "PDF:p1:parent",
        "accuracy_limitation": "Unknown; fixture only",
        "verification_note": "Synthetic existing reference",
        "reviewer": "SYNTHETIC FIXTURE REVIEWER",
        "reviewed_at": "2026-01-01T00:00:00Z",
    }
    original = {"version": 1, "records": {str(parent.id): approved_parent}}
    approve(candidate, path)
    row = preflight(db, [candidate], original)[0]
    assert "COLOCATION_REVIEW_REQUIRED" in row["reasons"]
    approve(
        candidate,
        path,
        resolved_conflicts=row["issues"],
        conflict_resolution="Synthetic reviewer confirms a shared complex reference, not building footprints",
        colocated_with=[str(parent.id)],
        colocation_basis="Fixture explicitly identifies one shared reference for these two assets",
    )
    result, rows = apply_candidates(db, original, [candidate], [candidate.candidate_id])
    assert rows[0]["status"] == "ELIGIBLE"
    assert result["records"][str(parent.id)] == approved_parent
    assert result["records"][str(asset.id)]["geometry"] == approved_parent["geometry"]
    assert len(result["records"]) == 2


def test_genuine_spatial_only_source_binding_does_not_require_or_mutate_engineering_records(
    reference, monkeypatch
):
    _, db, asset, candidate, path = reference
    monkeypatch.setattr(
        settings, "reviewed_provenance_path", path / "absent-provenance.json"
    )
    records_before = [
        (record.id, record.source_id, record.verification_status, record.value_text)
        for record in db.query(AssetTechnicalAttribute).filter(
            AssetTechnicalAttribute.asset_id == asset.id
        )
    ]
    approve(candidate, path)
    assert (
        "REVIEWED_EXACT_ASSET_SOURCE_BINDING_REQUIRED"
        in preflight(db, [candidate], {"version": 1, "records": {}})[0]["reasons"]
    )
    approve(candidate, path, source_binding_confirmed=True)
    row = preflight(db, [candidate], {"version": 1, "records": {}})[0]
    assert row["status"] == "ELIGIBLE"
    accepted, _ = apply_candidates(
        db, {"version": 1, "records": {}}, [candidate], [candidate.candidate_id]
    )
    assert accepted["records"][str(asset.id)]["source_id"] == str(candidate.source_id)
    assert accepted["records"][str(asset.id)]["document_id"] == str(
        candidate.document_id
    )
    assert asset.geometry is None
    assert records_before == [
        (record.id, record.source_id, record.verification_status, record.value_text)
        for record in db.query(AssetTechnicalAttribute).filter(
            AssetTechnicalAttribute.asset_id == asset.id
        )
    ]


def test_spatial_source_binding_flag_cannot_bypass_registered_document_or_candidate_receipt_hash(
    reference, monkeypatch
):
    _, db, _, candidate, path = reference
    monkeypatch.setattr(
        settings, "reviewed_provenance_path", path / "absent-provenance.json"
    )
    approve(candidate, path, source_binding_confirmed=True)
    candidate.coordinates.x = "106.34"
    row = preflight(db, [candidate], {"version": 1, "records": {}})[0]
    assert "REVIEW_CANDIDATE_HASH_MISMATCH" in row["reasons"]
    assert "REVIEWED_EXACT_ASSET_SOURCE_BINDING_REQUIRED" in row["reasons"]
    candidate.document_id = None
    approve(candidate, path, source_binding_confirmed=True)
    assert (
        "REGISTERED_SOURCE_DOCUMENT_BINDING_REQUIRED"
        in preflight(db, [candidate], {"version": 1, "records": {}})[0]["reasons"]
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/private.pdf",
        "http://10.0.0.1/private.pdf",
        "http://192.168.1.1/private.pdf",
        "http://[::1]/private.pdf",
        "https://intranet.local/private.pdf",
        "https://user:password@example.org/source.pdf",
        "https://example.org/source.pdf?access_token=private",
        "https://example.org/source.pdf?X-Amz-Credential=private",
        "https://example.org/source.pdf#access_token=private",
        "https://example.org/Users/reviewer/private.pdf",
    ],
)
def test_public_candidate_links_never_expose_local_or_keyed_sources(reference, url):
    from pydantic import HttpUrl

    from app.services.spatial_candidates import candidate_public

    _, _, _, candidate, _ = reference
    candidate.source_url = HttpUrl(url)
    public = candidate_public(candidate)
    assert public["source_url"] is None
    assert str(candidate.source_url) not in json.dumps(public)
    assert candidate.source_url is not None  # Private evidence is not edited.


def test_public_original_url_keeps_page_and_public_dataset_query(reference):
    from pydantic import HttpUrl

    from app.services.spatial_candidates import candidate_public

    _, _, _, candidate, _ = reference
    url = "https://example.org/source.pdf?id=521#page=22"
    candidate.source_url = HttpUrl(url)
    assert candidate_public(candidate)["source_url"] == url


def test_explicitly_rejected_source_cannot_be_accepted_by_spatial_receipt(reference):
    _, db, _, candidate, path = reference
    source = db.get(DataSource, candidate.source_id)
    source.verification_status = "REJECTED"
    db.flush()
    approve(candidate, path, source_binding_confirmed=True)
    pending = merge_candidates(db, {"version": 1, "records": {}}, [candidate], {})
    assert pending["records"] == {}  # A rejected source lead may remain traceable.
    row = preflight(db, [candidate], pending)[0]
    assert "SOURCE_REJECTED" in row["reasons"]
    with pytest.raises(ValueError, match="blocked"):
        apply_candidates(
            db, {"version": 1, "records": {}}, [candidate], [candidate.candidate_id]
        )
