import json
from uuid import UUID

from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_category import AssetCategory
from app.schemas.asset import AssetCategoryResponse, AssetResponse


def asset_query():
    return select(
        Asset.id,
        Asset.reservoir_id,
        Asset.parent_asset_id,
        Asset.asset_code,
        Asset.name,
        Asset.description,
        Asset.technical_description,
        Asset.condition_status,
        Asset.data_status,
        AssetCategory.id.label("category_id"),
        AssetCategory.code.label("category_code"),
        AssetCategory.name.label("category_name"),
        ST_AsGeoJSON(Asset.geometry).label("geometry"),
    ).join(AssetCategory, Asset.category_id == AssetCategory.id)


def serialize_asset(row) -> AssetResponse:
    values = dict(row)
    category = AssetCategoryResponse(
        id=values.pop("category_id"),
        code=values.pop("category_code"),
        name=values.pop("category_name"),
    )
    values["geometry"] = json.loads(values["geometry"]) if values["geometry"] else None
    return AssetResponse(**values, category=category)


def list_assets(db: Session, reservoir_id: UUID) -> list[AssetResponse]:
    rows = db.execute(
        asset_query()
        .where(Asset.reservoir_id == reservoir_id)
        .order_by(Asset.asset_code)
    ).mappings()
    return [serialize_asset(row) for row in rows]


def find_asset(db: Session, asset_id: UUID) -> AssetResponse | None:
    row = db.execute(asset_query().where(Asset.id == asset_id)).mappings().one_or_none()
    return serialize_asset(row) if row else None


def validate_parent(
    db: Session, reservoir_id: UUID, parent_asset_id: UUID | None, asset_id: UUID
) -> None:
    """Use for imports/reparenting; the composite FK also guards reservoir identity."""
    seen = {asset_id}
    current = parent_asset_id
    while current is not None:
        if current in seen:
            raise ValueError("Asset hierarchy cannot contain a cycle")
        seen.add(current)
        parent = db.get(Asset, current)
        if parent is None or parent.reservoir_id != reservoir_id:
            raise ValueError("Parent asset must exist in the same reservoir")
        current = parent.parent_asset_id
