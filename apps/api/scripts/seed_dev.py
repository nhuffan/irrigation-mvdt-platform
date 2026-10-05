"""Synthetic development fixtures only. Never represents verified physical assets."""

import argparse
import uuid

from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.asset_category import AssetCategory
from app.models.reservoir import Reservoir
from app.services.asset_service import validate_parent


def seed(reservoir_code: str) -> int:
    if settings.app_env != "development":
        raise ValueError("Development seed is disabled outside development")
    with SessionLocal.begin() as db:
        row = db.execute(
            select(
                Reservoir.id, ST_X(Reservoir.location), ST_Y(Reservoir.location)
            ).where(Reservoir.code == reservoir_code)
        ).one_or_none()
        if row is None:
            raise ValueError(
                f"Reservoir {reservoir_code!r} not found; run the reservoir seed first"
            )
        reservoir_id, x, y = row
        categories = {}
        for code, name in [
            ("STRUCTURE", "Structure"),
            ("EQUIPMENT", "Equipment"),
            ("CHANNEL", "Channel"),
            ("BUILDING", "Building"),
            ("OTHER", "Other"),
        ]:
            db.execute(
                insert(AssetCategory)
                .values(
                    id=uuid.uuid4(),
                    code=code,
                    name=name,
                    description="Development category; taxonomy subject to Phase 1 validation.",
                )
                .on_conflict_do_nothing(index_elements=["code"])
            )
            categories[code] = db.scalar(
                select(AssetCategory.id).where(AssetCategory.code == code)
            )
        # Arbitrary offsets intentionally illustrate geometry types, not actual infrastructure.
        fixtures = [
            (
                "001",
                "Development footprint",
                "STRUCTURE",
                f"SRID=4326;POLYGON(({x - 0.008} {y - 0.006},{x + 0.008} {y - 0.006},{x + 0.008} {y + 0.006},{x - 0.008} {y + 0.006},{x - 0.008} {y - 0.006}))",
                None,
            ),
            (
                "002",
                "Development channel",
                "CHANNEL",
                f"SRID=4326;LINESTRING({x + 0.012} {y - 0.01},{x + 0.02} {y},{x + 0.016} {y + 0.012})",
                "001",
            ),
            (
                "003",
                "Development equipment",
                "EQUIPMENT",
                f"SRID=4326;POINT({x - 0.015} {y + 0.005})",
                "001",
            ),
            ("004", "Development record without geometry", "OTHER", None, "001"),
        ]
        ids = {}
        created = 0
        for suffix, name, category, geometry, parent_suffix in fixtures:
            code = f"DEV-{reservoir_code}-{suffix}"
            existing = db.execute(
                select(Asset.id, Asset.reservoir_id).where(Asset.asset_code == code)
            ).one_or_none()
            if existing:
                if existing.reservoir_id != reservoir_id:
                    raise ValueError(f"Asset code {code} belongs to another reservoir")
                ids[suffix] = existing.id
                continue
            asset_id = uuid.uuid4()
            parent_id = ids.get(parent_suffix)
            validate_parent(db, reservoir_id, parent_id, asset_id)
            db.add(
                Asset(
                    id=asset_id,
                    reservoir_id=reservoir_id,
                    category_id=categories[category],
                    parent_asset_id=parent_id,
                    asset_code=code,
                    name=name,
                    description="Synthetic development asset. Identity and geometry are not verified research data.",
                    technical_description="Illustrative fixture for Stage 2 integration testing; no engineering specifications verified.",
                    condition_status=None,
                    data_status="REGISTERED",
                    geometry=geometry,
                )
            )
            db.flush()
            ids[suffix] = asset_id
            created += 1
        return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reservoir-code", default="DT001")
    args = parser.parse_args()
    print(
        f"Created {seed(args.reservoir_code)} development assets; reservoir maturity unchanged."
    )

    from scripts.seed_om import seed_om

    print(
        f"Created {seed_om(args.reservoir_code)} synthetic O&M records; all remain UNVERIFIED."
    )
