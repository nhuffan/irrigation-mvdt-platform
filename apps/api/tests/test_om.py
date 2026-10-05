from datetime import date
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import get_db
from app.main import app
from app.models.asset import Asset
from app.models.asset_condition import AssetCondition
from app.models.asset_technical_attribute import AssetTechnicalAttribute
from app.models.data_source import DataSource
from app.models.inspection import Inspection
from app.models.maintenance_record import MaintenanceRecord
from app.models.repair import Repair
from app.services.source_service import validate_source_link

KINDS = ["technical", "conditions", "inspections", "repairs", "maintenance", "timeline"]


@pytest.fixture
def om_domain(domain):
    client, db, reservoir, empty, _category, assets = domain
    source = DataSource(
        id=uuid4(),
        reservoir_id=reservoir.id,
        source_code=f"TEST-{uuid4()}",
        source_type="OTHER",
        title="Test source",
        verification_status="UNVERIFIED",
    )
    source_b = DataSource(
        id=uuid4(),
        reservoir_id=reservoir.id,
        source_code=f"TEST-{uuid4()}",
        source_type="DRAWING",
        title="Test conflicting source",
        verification_status="VERIFIED",
    )
    db.add_all([source, source_b])
    db.flush()
    common = {"asset_id": assets[0].id, "source_id": source.id}
    records = [
        AssetTechnicalAttribute(
            **common,
            attribute_key="width",
            attribute_label="Width A",
            value_number=4.0,
            unit="m",
        ),
        AssetTechnicalAttribute(
            asset_id=assets[0].id,
            source_id=source_b.id,
            attribute_key="width",
            attribute_label="Width B",
            value_number=4.2,
            unit="m",
        ),
        AssetTechnicalAttribute(
            asset_id=assets[0].id,
            attribute_key="missing",
            attribute_label="Missing value",
        ),
        AssetTechnicalAttribute(
            **common, attribute_key="zero", attribute_label="Real zero", value_number=0
        ),
    ]
    dates = [date(2025, 1, 1), date(2024, 1, 1), date(2026, 1, 1)]
    for day in dates:
        records.extend(
            [
                AssetCondition(
                    **common,
                    condition_date=day,
                    condition_status="REVIEW",
                    verification_status="UNVERIFIED"
                    if day.year == 2026
                    else "VERIFIED",
                ),
                Inspection(**common, inspection_date=day),
                Repair(**common, repair_date=day, repair_description="Repair example"),
                MaintenanceRecord(
                    **common, maintenance_date=day, description="Maintenance example"
                ),
            ]
        )
    records.append(
        AssetCondition(
            **common,
            condition_date=date(2027, 1, 1),
            condition_status="REJECTED REVIEW",
            verification_status="REJECTED",
        )
    )
    db.add_all(records)
    db.flush()
    return client, db, assets, source, source_b, reservoir, empty


@pytest.mark.parametrize("kind", KINDS)
def test_existing_empty_asset_returns_empty_array(om_domain, kind):
    client, _, assets, *_ = om_domain
    response = client.get(f"/api/v1/assets/{assets[1].id}/{kind}")
    assert response.status_code == 200 and response.json() == []


@pytest.mark.parametrize("kind", [*KINDS, "current-condition"])
@pytest.mark.parametrize("value,status", [("invalid", 422), (str(uuid4()), 404)])
def test_bad_asset_ids(om_domain, kind, value, status):
    client, *_ = om_domain
    assert client.get(f"/api/v1/assets/{value}/{kind}").status_code == status


def test_technical_conflicts_null_and_zero_keep_their_meaning(om_domain):
    client, _, assets, source, source_b, *_ = om_domain
    response = client.get(f"/api/v1/assets/{assets[0].id}/technical")
    assert response.status_code == 200
    rows = response.json()
    values = [r for r in rows if r["attribute_key"] == "width"]
    assert {r["value_number"] for r in values} == {4.0, 4.2}
    assert {r["source"]["id"] for r in values} == {str(source.id), str(source_b.id)}
    missing = next(r for r in rows if r["attribute_key"] == "missing")
    assert missing["value_number"] is None and missing["value_text"] is None
    assert missing["source"] is None and missing["source_id"] is None
    assert next(r for r in rows if r["attribute_key"] == "zero")["value_number"] == 0


@pytest.mark.parametrize(
    "kind,key",
    [
        ("conditions", "condition_date"),
        ("inspections", "inspection_date"),
        ("repairs", "repair_date"),
        ("maintenance", "maintenance_date"),
    ],
)
def test_history_is_descending_and_sourced(om_domain, kind, key):
    client, _, assets, source, *_ = om_domain
    response = client.get(f"/api/v1/assets/{assets[0].id}/{kind}")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) >= 3
    assert [r[key] for r in rows] == sorted([r[key] for r in rows], reverse=True)
    assert rows[0]["source"]["source_code"] == source.source_code
    assert rows[0]["source"]["source_date"] is None


def test_current_condition_ignores_newer_unverified_and_rejected(om_domain):
    client, _, assets, *_ = om_domain
    response = client.get(f"/api/v1/assets/{assets[0].id}/current-condition")
    assert response.status_code == 200
    assert response.json()["condition_date"] == "2025-01-01"
    assert response.json()["verification_status"] == "VERIFIED"
    assert response.json()["summary"] is None
    missing = client.get(f"/api/v1/assets/{assets[1].id}/current-condition")
    assert missing.status_code == 200 and missing.json() is None


def test_timeline_merges_each_record_once_with_stable_dates(om_domain):
    client, _, assets, *_ = om_domain
    prefix = f"/api/v1/assets/{assets[0].id}"
    response = client.get(prefix + "/timeline")
    assert response.status_code == 200
    events = response.json()
    expected = {
        r["id"]
        for kind in ["conditions", "inspections", "repairs", "maintenance"]
        for r in client.get(prefix + "/" + kind).json()
    }
    assert len(events) == len(expected) == 13
    assert {e["record_id"] for e in events} == expected
    assert {e["event_type"] for e in events} == {
        "CONDITION",
        "INSPECTION",
        "REPAIR",
        "MAINTENANCE",
    }
    assert [e["event_date"] for e in events] == sorted(
        [e["event_date"] for e in events], reverse=True
    )
    assert events == client.get(prefix + "/timeline").json()
    assert all(e["source"] is not None for e in events)


def test_source_detail_and_unknown_ids(om_domain):
    client, _, _, source, *_ = om_domain
    response = client.get(f"/api/v1/data-sources/{source.id}")
    assert response.status_code == 200 and response.json()["title"] == "Test source"
    assert client.get(f"/api/v1/data-sources/{uuid4()}").status_code == 404
    assert client.get("/api/v1/data-sources/invalid").status_code == 422


@pytest.mark.parametrize(
    "model,values",
    [
        (AssetTechnicalAttribute, {"attribute_key": "test", "attribute_label": "Test"}),
        (
            AssetCondition,
            {"condition_date": date(2025, 1, 1), "condition_status": "REVIEW"},
        ),
        (Inspection, {"inspection_date": date(2025, 1, 1)}),
        (Repair, {"repair_date": date(2025, 1, 1), "repair_description": "Test"}),
        (
            MaintenanceRecord,
            {"maintenance_date": date(2025, 1, 1), "description": "Test"},
        ),
    ],
)
def test_record_cannot_reference_missing_asset_or_source(om_domain, model, values):
    _, db, assets, *_ = om_domain
    for links in [
        {"asset_id": uuid4()},
        {"asset_id": assets[0].id, "source_id": uuid4()},
    ]:
        with pytest.raises(IntegrityError), db.begin_nested():
            db.add(model(**links, **values))
            db.flush()


def test_source_requires_reservoir_and_used_source_is_restricted(om_domain):
    _, db, _, source, *_ = om_domain
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            DataSource(
                reservoir_id=uuid4(),
                source_code=str(uuid4()),
                source_type="OTHER",
                title="Missing reservoir",
            )
        )
        db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(delete(DataSource).where(DataSource.id == source.id))


def test_asset_delete_cascades_records_but_preserves_source(om_domain):
    _, db, assets, source, *_ = om_domain
    asset_id = assets[0].id
    db.execute(delete(Asset).where(Asset.id == asset_id))
    for model in [
        AssetTechnicalAttribute,
        AssetCondition,
        Inspection,
        Repair,
        MaintenanceRecord,
    ]:
        assert (
            db.scalar(
                select(func.count())
                .select_from(model)
                .where(model.asset_id == asset_id)
            )
            == 0
        )
    assert db.get(DataSource, source.id) is not None


def test_import_rejects_cross_reservoir_source(om_domain):
    _, db, assets, _, _, _, empty = om_domain
    other = DataSource(
        reservoir_id=empty.id,
        source_code=str(uuid4()),
        source_type="OTHER",
        title="Other reservoir",
    )
    db.add(other)
    db.flush()
    with pytest.raises(ValueError, match="reservoir"):
        validate_source_link(db, assets[0].id, other.id)


def test_database_failure_is_500_not_empty_or_404():
    broken_db = Mock()
    broken_db.scalar.side_effect = SQLAlchemyError("test unavailable")
    app.dependency_overrides[get_db] = lambda: broken_db
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            for kind in [*KINDS, "current-condition"]:
                assert client.get(f"/api/v1/assets/{uuid4()}/{kind}").status_code == 500
    finally:
        app.dependency_overrides.pop(get_db, None)
