from uuid import UUID

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.data_source import DataSource


def validate_source_link(db: Session, asset_id: UUID, source_id: UUID | None) -> None:
    """Validate before future imports; no O&M write API is exposed in Stage 3."""
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise ValueError("Asset does not exist")
    if source_id is not None:
        source = db.get(DataSource, source_id)
        if source is None or source.reservoir_id != asset.reservoir_id:
            raise ValueError("Source must exist in the asset's reservoir")
