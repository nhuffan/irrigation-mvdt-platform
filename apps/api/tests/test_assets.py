"""PostGIS integration tests; temporary records are rolled back after each test."""

from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DataError, IntegrityError

from app.models.asset import Asset
from app.services.asset_service import validate_parent


def test_list_and_detail_geojson_hierarchy_category(domain):
    client, _, reservoir, _, category, assets = domain
    response = client.get(f"/api/v1/reservoirs/{reservoir.id}/assets")
    assert response.status_code == 200
    rows = {row["id"]: row for row in response.json()}
    assert len(rows) == 4
    for asset, kind in zip(
        assets, ["Polygon", "LineString", "Point", None], strict=True
    ):
        row = rows[str(asset.id)]
        assert row["category"] == {
            "id": str(category.id),
            "code": category.code,
            "name": category.name,
        }
        assert row["parent_asset_id"] == (
            str(assets[0].id) if asset.parent_asset_id else None
        )
        assert row["condition_status"] is None
        assert (row["geometry"]["type"] if row["geometry"] else None) == kind
        detail = client.get(f"/api/v1/assets/{asset.id}")
        assert detail.status_code == 200 and detail.json() == row
    assert rows[str(assets[2].id)]["geometry"]["coordinates"] == [106.05, 11.05]


def test_empty_reservoir_is_empty_list(domain):
    client, _, _, empty, _, _ = domain
    response = client.get(f"/api/v1/reservoirs/{empty.id}/assets")
    assert response.status_code == 200 and response.json() == []


@pytest.mark.parametrize("path", ["/api/v1/assets/{}", "/api/v1/reservoirs/{}/assets"])
@pytest.mark.parametrize("value,status", [("invalid", 422), (str(uuid4()), 404)])
def test_invalid_and_unknown_resources(domain, path, value, status):
    client, *_ = domain
    assert client.get(path.format(value)).status_code == status


def test_parent_must_belong_to_same_reservoir(domain):
    _, db, _, empty, _, assets = domain
    with pytest.raises(ValueError, match="same reservoir"):
        validate_parent(db, empty.id, assets[0].id, uuid4())
    # The database independently prevents cross-reservoir parents on any write path.
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(
            update(Asset).where(Asset.id == assets[1].id).values(reservoir_id=empty.id)
        )


def test_cycles_rejected_by_import_validator(domain):
    _, db, reservoir, _, _, assets = domain
    with pytest.raises(ValueError, match="cycle"):
        validate_parent(db, reservoir.id, assets[1].id, assets[0].id)
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(
            update(Asset)
            .where(Asset.id == assets[0].id)
            .values(parent_asset_id=assets[0].id)
        )


def test_parent_deletion_keeps_child_reservoir(domain):
    _, db, reservoir, _, _, assets = domain
    db.execute(delete(Asset).where(Asset.id == assets[0].id))
    row = db.execute(
        select(Asset.reservoir_id, Asset.parent_asset_id).where(
            Asset.id == assets[1].id
        )
    ).one()
    assert row.reservoir_id == reservoir.id and row.parent_asset_id is None


def test_asset_code_is_globally_unique(domain):
    _, db, _, _, _, assets = domain
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(
            update(Asset)
            .where(Asset.id == assets[1].id)
            .values(asset_code=assets[0].asset_code)
        )


@pytest.mark.parametrize(
    "wkt",
    [
        "SRID=4326;POINT(181 10)",
        "SRID=4326;MULTIPOINT((106 11),(107 12))",
        "SRID=4326;POINT EMPTY",
        "SRID=4326;POLYGON((106 11,107 12,107 11,106 12,106 11))",
        "SRID=3857;POINT(106 11)",
    ],
)
def test_invalid_geometry_rejected(domain, wkt):
    _, db, _, _, _, assets = domain
    with pytest.raises((IntegrityError, DataError)), db.begin_nested():
        db.execute(
            text("UPDATE assets SET geometry=ST_GeomFromEWKT(:wkt) WHERE id=:id"),
            {"wkt": wkt, "id": assets[2].id},
        )
