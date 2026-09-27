"""Integration checks against local PostGIS; all test data is rolled back."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.main import app


@pytest.fixture
def reservoir_client():
    reservoir_id = uuid4()
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection)
        session.execute(
            text("""
            INSERT INTO reservoirs (id, code, name, province, data_status,
                mvdt_level, description, location)
            VALUES (:id, :code, 'Integration Reservoir', NULL, 'DATA_COLLECTION',
                1, NULL, ST_SetSRID(ST_MakePoint(106.25, 11.75), 4326))
        """),
            {"id": reservoir_id, "code": f"TEST-{reservoir_id}"},
        )
        app.dependency_overrides[get_db] = lambda: session
        try:
            with TestClient(app) as client:
                yield client, reservoir_id
        finally:
            app.dependency_overrides.pop(get_db, None)
            session.close()
            transaction.rollback()


def test_detail_uses_database_coordinates_and_nullable_fields(reservoir_client):
    client, reservoir_id = reservoir_client
    response = client.get(f"/api/v1/reservoirs/{reservoir_id}")
    assert response.status_code == 200
    row = response.json()
    assert row["id"] == str(reservoir_id)
    assert (row["longitude"], row["latitude"]) == (106.25, 11.75)
    assert row["province"] is None
    assert row["description"] is None
    assert row["data_status"] == "DATA_COLLECTION"
    assert row["mvdt_level"] == 1
    listing = client.get("/api/v1/reservoirs")
    assert listing.status_code == 200
    assert row in listing.json()


def test_missing_uuid_is_404(reservoir_client):
    client, _ = reservoir_client
    response = client.get(f"/api/v1/reservoirs/{uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Reservoir not found"}


def test_malformed_uuid_is_422(reservoir_client):
    client, _ = reservoir_client
    assert client.get("/api/v1/reservoirs/not-a-uuid").status_code == 422
