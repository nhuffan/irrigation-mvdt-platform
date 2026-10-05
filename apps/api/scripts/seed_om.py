"""Synthetic, unverified O&M examples. No engineering or research claims."""

from datetime import date
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.asset_category import AssetCategory  # noqa: F401
from app.models.asset_condition import AssetCondition
from app.models.asset_technical_attribute import AssetTechnicalAttribute
from app.models.data_source import DataSource
from app.models.inspection import Inspection
from app.models.maintenance_record import MaintenanceRecord
from app.models.repair import Repair
from app.models.reservoir import Reservoir  # noqa: F401
from app.services.source_service import validate_source_link


def seed_om(reservoir_code: str) -> int:
    if settings.app_env != "development":
        raise ValueError("Development seed is disabled outside development")
    with SessionLocal.begin() as db:
        asset = db.scalar(
            select(Asset).where(Asset.asset_code == f"DEV-{reservoir_code}-003")
        )
        if asset is None:
            raise ValueError("Run the development asset seed first")
        source_code = f"DEV-{reservoir_code}-OM-001"
        source_id = uuid5(NAMESPACE_URL, f"mvdt:stage3:{source_code}")
        db.execute(
            insert(DataSource)
            .values(
                id=source_id,
                reservoir_id=asset.reservoir_id,
                source_code=source_code,
                source_type="OTHER",
                title="DEVELOPMENT ONLY — synthetic O&M fixture",
                file_name=None,
                source_date=date(2025, 3, 1),
                source_owner="Development fixture generator",
                authority_level=None,
                verification_status="UNVERIFIED",
                notes="Invented software test records, not real inspections, repairs, maintenance or research evidence.",
            )
            .on_conflict_do_nothing(index_elements=["source_code"])
        )
        source = db.scalar(
            select(DataSource).where(DataSource.source_code == source_code)
        )
        validate_source_link(db, asset.id, source.id)
        fixtures = [
            (
                AssetTechnicalAttribute,
                "width-a",
                {
                    "attribute_key": "demo_width",
                    "attribute_label": "Demo width (candidate A)",
                    "value_number": 4.0,
                    "unit": "m",
                },
            ),
            (
                AssetTechnicalAttribute,
                "width-b",
                {
                    "attribute_key": "demo_width",
                    "attribute_label": "Demo width (candidate B)",
                    "value_number": 4.2,
                    "unit": "m",
                },
            ),
            (
                AssetTechnicalAttribute,
                "material",
                {
                    "attribute_key": "demo_material",
                    "attribute_label": "Demo material",
                    "value_text": "Steel (illustrative only)",
                },
            ),
            (
                AssetTechnicalAttribute,
                "year-missing",
                {
                    "attribute_key": "construction_year",
                    "attribute_label": "Construction year",
                    "value_number": None,
                },
            ),
            (
                AssetCondition,
                "condition-1",
                {
                    "condition_date": date(2024, 3, 15),
                    "condition_status": "DEMO_REVIEW_REQUIRED",
                    "summary": "DEV ONLY — simulated condition observation.",
                    "defect_description": None,
                    "recommended_action": "DEV ONLY — review source information.",
                },
            ),
            (
                AssetCondition,
                "condition-2",
                {
                    "condition_date": date(2025, 1, 10),
                    "condition_status": "DEMO_PENDING_ASSESSMENT",
                    "summary": "DEV ONLY — newer unverified observation.",
                    "defect_description": "DEV ONLY — illustrative surface wear.",
                    "recommended_action": None,
                },
            ),
            (
                Inspection,
                "inspection-1",
                {
                    "inspection_date": date(2024, 3, 15),
                    "inspection_type": "DEV periodic inspection",
                    "inspector": "Development fixture",
                    "summary": "DEV ONLY — illustrative inspection.",
                    "observation": "DEV ONLY — observation placeholder.",
                    "condition_status": None,
                },
            ),
            (
                Inspection,
                "inspection-2",
                {
                    "inspection_date": date(2025, 1, 10),
                    "inspection_type": "DEV follow-up",
                    "inspector": None,
                    "summary": "DEV ONLY — illustrative follow-up.",
                    "observation": None,
                    "recommended_action": "DEV ONLY — seek verified inspection report.",
                },
            ),
            (
                Repair,
                "repair-1",
                {
                    "repair_date": date(2024, 6, 20),
                    "repair_type": "DEV repair",
                    "problem_description": "DEV ONLY — illustrative problem.",
                    "repair_description": "DEV ONLY — simulated component adjustment.",
                    "result": None,
                    "responsible_unit": "Development fixture",
                },
            ),
            (
                MaintenanceRecord,
                "maintenance-1",
                {
                    "maintenance_date": date(2024, 3, 15),
                    "maintenance_type": "DEV routine",
                    "description": "DEV ONLY — simulated routine maintenance.",
                    "result": None,
                },
            ),
            (
                MaintenanceRecord,
                "maintenance-2",
                {
                    "maintenance_date": date(2025, 3, 1),
                    "maintenance_type": "DEV follow-up",
                    "description": "DEV ONLY — simulated follow-up maintenance.",
                    "responsible_unit": "Development fixture",
                    "result": "DEV ONLY — test record complete.",
                },
            ),
        ]
        created = 0
        for model, key, values in fixtures:
            record_id = uuid5(NAMESPACE_URL, f"mvdt:stage3:{asset.id}:{key}")
            result = db.execute(
                insert(model)
                .values(
                    id=record_id,
                    asset_id=asset.id,
                    source_id=source.id,
                    verification_status="UNVERIFIED",
                    **values,
                )
                .on_conflict_do_nothing(index_elements=["id"])
                .returning(model.id)
            )
            created += result.scalar_one_or_none() is not None
        return created
