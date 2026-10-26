"""Targeted checks: reference overlays cannot promote or overwrite DB geometry."""

import json
from uuid import uuid4

import pytest

from app.core.config import settings
from app.schemas.asset import AssetCategoryResponse, AssetResponse, PointGeometry
from app.services.asset_location import asset_location


def asset(geometry=None, code="RS-TEST"):
    return AssetResponse(
        id=uuid4(),
        reservoir_id=uuid4(),
        parent_asset_id=None,
        asset_code=code,
        name="Test",
        description=None,
        technical_description=None,
        condition_status=None,
        data_status="VERIFIED",
        category=AssetCategoryResponse(id=uuid4(), code="TEST", name="Test"),
        geometry=geometry,
    )


def entry(a):
    return {
        "asset_id": str(a.id),
        "reservoir_id": str(a.reservoir_id),
        "asset_code": a.asset_code,
        "location_status": "REFERENCE_LOCATION",
        "geometry": {"type": "Point", "coordinates": [106, 11]},
        "crs": "EPSG:4326",
        "source": "Test map",
        "locator": "p1 symbol",
        "accuracy_limitation": "Reference only",
        "verification_note": "Not F02",
        "reviewer": "Test reviewer",
        "reviewed_at": "2026-10-14T00:00:00+07:00",
    }


def sidecar(tmp_path, monkeypatch, a, review):
    p = tmp_path / "locations.json"
    p.write_text(json.dumps({"version": 1, "records": {str(a.id): review}}))
    monkeypatch.setattr(settings, "asset_locations_path", p)


def test_reference_overlay_does_not_fill_db_geometry(tmp_path, monkeypatch):
    a = asset()
    sidecar(tmp_path, monkeypatch, a, entry(a))
    result = asset_location(a)
    assert a.geometry is None
    assert result.location_status == "REFERENCE_LOCATION"
    assert result.geometry.coordinates == (106, 11)
    assert result.review_state == "AVAILABLE"


def test_no_sidecar_never_infers_verification(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "asset_locations_path", tmp_path / "absent.json")
    assert asset_location(asset()).location_status == "NO_LOCATION"
    a = asset(PointGeometry(type="Point", coordinates=(106, 11)))
    assert asset_location(a).location_status == "REFERENCE_LOCATION"


@pytest.mark.parametrize(
    "change",
    [
        {"asset_code": "RS-WRONG"},
        {"reservoir_id": str(uuid4())},
        {"geometry": {"type": "Point", "coordinates": [181, 11]}},
        {"crs": "EPSG:32648"},
        {"source": " "},
        {"location_status": "VERIFIED_GEOMETRY"},
    ],
)
def test_invalid_or_unbound_review_cannot_create_a_location(
    tmp_path, monkeypatch, change
):
    a = asset()
    e = entry(a)
    e.update(change)
    sidecar(tmp_path, monkeypatch, a, e)
    result = asset_location(a)
    assert result.location_status == "NO_LOCATION" and result.geometry is None
    assert result.review_state == "UNAVAILABLE"


def test_verified_geometry_requires_exact_existing_rs_geometry(tmp_path, monkeypatch):
    a = asset(PointGeometry(type="Point", coordinates=(106, 11)))
    e = entry(a)
    e["location_status"] = "VERIFIED_GEOMETRY"
    sidecar(tmp_path, monkeypatch, a, e)
    assert asset_location(a).location_status == "VERIFIED_GEOMETRY"
    a.geometry = PointGeometry(type="Point", coordinates=(107, 11))
    assert asset_location(a).location_status == "REFERENCE_LOCATION"
    a.asset_code = "DEV-TEST"
    e = entry(a)
    e["location_status"] = "VERIFIED_GEOMETRY"
    sidecar(tmp_path, monkeypatch, a, e)
    assert asset_location(a).location_status == "REFERENCE_LOCATION"


def test_accepted_location_does_not_publish_keyed_source_url(tmp_path, monkeypatch):
    a = asset()
    review = entry(a)
    review["source_url"] = "https://example.org/source.pdf?token=private"
    sidecar(tmp_path, monkeypatch, a, review)
    result = asset_location(a)
    assert result.location_status == "REFERENCE_LOCATION"
    assert result.source_url is None
    assert result.geometry.coordinates == (106, 11)


@pytest.mark.parametrize("candidates", [None, "malformed", [None], {}])
def test_malformed_candidate_metadata_cannot_remove_an_accepted_reference(
    tmp_path, monkeypatch, candidates
):
    a = asset()
    accepted = entry(a) | {
        "evidence_id": "accepted-revision",
        "source_sha256": "1" * 64,
    }
    path = tmp_path / "locations.json"
    path.write_text(
        json.dumps(
            {"version": 1, "records": {str(a.id): accepted}, "candidates": candidates}
        )
    )
    monkeypatch.setattr(settings, "asset_locations_path", path)
    result = asset_location(a)
    assert result.location_status == "REFERENCE_LOCATION"
    assert result.geometry.coordinates == (106, 11)
    assert a.geometry is None
