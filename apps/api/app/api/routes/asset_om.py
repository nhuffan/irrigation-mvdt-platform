from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.condition import AssetConditionResponse
from app.schemas.inspection import InspectionResponse
from app.schemas.maintenance import MaintenanceRecordResponse
from app.schemas.repair import RepairResponse
from app.schemas.technical_attribute import AssetTechnicalAttributeResponse
from app.schemas.timeline import TimelineEvent
from app.services import om_service

router = APIRouter(prefix="/assets", tags=["asset O&M"])


@router.get(
    "/{asset_id}/technical", response_model=list[AssetTechnicalAttributeResponse]
)
def get_technical(asset_id: UUID, db: Annotated[Session, Depends(get_db)]):
    om_service.require_asset(db, asset_id)
    return om_service.list_records(db, asset_id, "technical")


@router.get("/{asset_id}/conditions", response_model=list[AssetConditionResponse])
def get_conditions(asset_id: UUID, db: Annotated[Session, Depends(get_db)]):
    om_service.require_asset(db, asset_id)
    return om_service.list_records(db, asset_id, "conditions")


@router.get("/{asset_id}/inspections", response_model=list[InspectionResponse])
def get_inspections(asset_id: UUID, db: Annotated[Session, Depends(get_db)]):
    om_service.require_asset(db, asset_id)
    return om_service.list_records(db, asset_id, "inspections")


@router.get("/{asset_id}/repairs", response_model=list[RepairResponse])
def get_repairs(asset_id: UUID, db: Annotated[Session, Depends(get_db)]):
    om_service.require_asset(db, asset_id)
    return om_service.list_records(db, asset_id, "repairs")


@router.get("/{asset_id}/maintenance", response_model=list[MaintenanceRecordResponse])
def get_maintenance(asset_id: UUID, db: Annotated[Session, Depends(get_db)]):
    om_service.require_asset(db, asset_id)
    return om_service.list_records(db, asset_id, "maintenance")


@router.get("/{asset_id}/timeline", response_model=list[TimelineEvent])
def get_timeline(asset_id: UUID, db: Annotated[Session, Depends(get_db)]):
    om_service.require_asset(db, asset_id)
    return om_service.timeline(db, asset_id)


@router.get(
    "/{asset_id}/current-condition", response_model=AssetConditionResponse | None
)
def get_current_condition(asset_id: UUID, db: Annotated[Session, Depends(get_db)]):
    om_service.require_asset(db, asset_id)
    return om_service.current_condition(db, asset_id)
