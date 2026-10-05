"""PostGIS integration tests; temporary records are rolled back after each test."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.main import app
from app.models.asset import Asset
from app.models.asset_category import AssetCategory
from app.models.reservoir import Reservoir


@pytest.fixture
def domain():
    with engine.connect() as connection:
        transaction = connection.begin()
        db = Session(bind=connection)
        reservoir = Reservoir(
            id=uuid4(),
            code=f"T-{uuid4()}",
            name="Test reservoir",
            location="SRID=4326;POINT(106 11)",
        )
        empty = Reservoir(
            id=uuid4(),
            code=f"T-{uuid4()}",
            name="Empty reservoir",
            location="SRID=4326;POINT(107 12)",
        )
        category = AssetCategory(id=uuid4(), code=f"T-{uuid4()}", name="Test category")
        db.add_all([reservoir, empty, category])
        db.flush()
        assets = []
        for geometry in [
            "SRID=4326;POLYGON((106 11,106.1 11,106.1 11.1,106 11.1,106 11))",
            "SRID=4326;LINESTRING(106 11,106.1 11.1)",
            "SRID=4326;POINT(106.05 11.05)",
            None,
        ]:
            asset = Asset(
                id=uuid4(),
                reservoir_id=reservoir.id,
                category_id=category.id,
                parent_asset_id=assets[0].id if assets else None,
                asset_code=f"TEST-{uuid4()}",
                name="Test asset",
                data_status="REGISTERED",
                geometry=geometry,
            )
            db.add(asset)
            db.flush()
            assets.append(asset)
        app.dependency_overrides[get_db] = lambda: db
        try:
            with TestClient(app) as client:
                yield client, db, reservoir, empty, category, assets
        finally:
            app.dependency_overrides.pop(get_db, None)
            db.close()
            transaction.rollback()
