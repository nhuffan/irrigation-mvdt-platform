from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.asset import AssetResponse
from app.services.asset_service import find_asset

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: UUID, db: Annotated[Session, Depends(get_db)]) -> AssetResponse:
    asset = find_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
