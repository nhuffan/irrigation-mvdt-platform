"""Synthetic B01B gate tests; no research approvals are inferred."""

from copy import deepcopy
from uuid import uuid4

import pytest

from scripts.prepare_reviewed_asset_batch import compile_batch, validate_geometry


def inputs():
    stamp = {"reviewer": "TEST", "reviewed_at": "2026-10-08T00:00:00+00:00"}
    targets = [
        {
            "target_asset_code": "RS-A",
            "target_asset_name": "Test",
            "category": "RS-CAT-A",
            "parent_asset_code": "",
            "expected_geometry_type": "Point",
            "in_scope": "true",
            "requires_3d": "false",
            "verification_status": "VERIFIED",
        }
    ]
    identities = [
        {
            "asset_code": "RS-A",
            "canonical_name": "Test",
            "category_code": "RS-CAT-A",
            "parent_asset_code": "",
            "in_scope": "true",
            "identity_status": "VERIFIED",
            "primary_evidence": "E1",
            "secondary_evidence": "",
            "rationale": "TEST",
            **stamp,
        }
    ]
    geometries = [
        {
            "asset_code": "RS-A",
            "expected_geometry_type": "Point",
            "geometry_status": "NOT_AVAILABLE",
            "survey_grade": "false",
            "notes": "TEST missing geometry",
            "geometry_geojson": "",
            **stamp,
        }
    ]
    evidence = [
        {
            "evidence_id": "E1",
            "source_code": "RS-S",
            "drive_file_id": "TEST",
            "file_name": "TEST.pdf",
            "mime_type": "application/pdf",
            "asset_codes": "RS-A",
            "purpose": "IDENTITY|GEOMETRY",
            "review_status": "REVIEWED",
            **stamp,
        }
    ]
    ids = [
        {"record_type": k, "code": c, "uuid": str(uuid4())}
        for k, c in [
            ("assets", "RS-A"),
            ("asset_categories", "RS-CAT-A"),
            ("data_sources", "RS-S"),
        ]
    ]
    return [targets, identities, geometries, evidence, ids, str(uuid4()), "TEST"]


def test_reuses_uuid_missing_geometry_and_no_input_mutation():
    values = inputs()
    before = deepcopy(values)
    batch = compile_batch(*values)
    record = batch["records"]["assets"][0]
    assert record["id"] == values[4][0]["uuid"]
    assert record["geometry"] is None and record["data_status"] == "REGISTERED"
    assert (
        record["technical_description"] is None and record["condition_status"] is None
    )
    assert values == before


@pytest.mark.parametrize(
    "group,key,value",
    [
        (0, "verification_status", "UNVERIFIED"),
        (0, "in_scope", "yes"),
        (1, "identity_status", "PARTIALLY_VERIFIED"),
        (1, "canonical_name", "Different"),
        (1, "primary_evidence", "UNKNOWN"),
        (1, "reviewer", ""),
        (1, "reviewed_at", "2026-10-08"),
        (2, "geometry_status", "VERIFIED"),
        (2, "survey_grade", "true"),
        (3, "review_status", "PENDING"),
        (3, "asset_codes", "RS-OTHER"),
        (3, "mime_type", "application/vnd.google-apps.folder"),
        (3, "purpose", "REFERENCE"),
    ],
)
def test_review_gates(group, key, value):
    values = inputs()
    values[group][0][key] = value
    with pytest.raises(ValueError):
        compile_batch(*values)


@pytest.mark.parametrize(
    "geometry,expected",
    [
        ({"type": "Point", "coordinates": [181, 10]}, "Point"),
        ({"type": "Point", "coordinates": [10, float("nan")]}, "Point"),
        ({"type": "Point", "coordinates": [True, 10]}, "Point"),
        ({"type": "Point", "coordinates": [106, 10]}, "Polygon"),
        ({"type": "LineString", "coordinates": [[1, 1]]}, "LineString"),
        (
            {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
            "Polygon",
        ),
        (
            {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]],
            },
            "Polygon",
        ),
    ],
)
def test_invalid_geojson(geometry, expected):
    with pytest.raises(ValueError):
        validate_geometry(geometry, expected)


def test_reviewed_point_and_source_mismatch():
    values = inputs()
    values[2][0].update(
        geometry_status="PARTIALLY_VERIFIED",
        geometry_geojson='{"type":"Point","coordinates":[106,11]}',
        output_crs="EPSG:4326",
        source_crs="EPSG:4326",
        working_crs="EPSG:4326",
        geometry_method="TEST",
        location_confidence="LOW",
        geometry_source="E1",
        source_file_id="TEST",
        evidence_reference="E1",
    )
    assert compile_batch(*values)["records"]["assets"][0]["geometry"][
        "coordinates"
    ] == [106, 11]
    values[2][0]["source_file_id"] = "WRONG"
    with pytest.raises(ValueError, match="source file"):
        compile_batch(*values)


def test_hierarchy_cycle_and_missing_uuid():
    values = inputs()
    values[0][0]["parent_asset_code"] = "RS-A"
    values[1][0]["parent_asset_code"] = "RS-A"
    with pytest.raises(ValueError, match="cycle"):
        compile_batch(*values)
    values = inputs()
    values[4].pop(0)
    with pytest.raises(ValueError, match="reserved UUID"):
        compile_batch(*values)
