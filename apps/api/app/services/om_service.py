from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.asset import Asset
from app.models.asset_condition import AssetCondition
from app.models.asset_technical_attribute import AssetTechnicalAttribute
from app.models.inspection import Inspection
from app.models.maintenance_record import MaintenanceRecord
from app.models.repair import Repair
from app.schemas.condition import AssetConditionResponse
from app.schemas.inspection import InspectionResponse
from app.schemas.maintenance import MaintenanceRecordResponse
from app.schemas.repair import RepairResponse
from app.schemas.technical_attribute import AssetTechnicalAttributeResponse
from app.schemas.timeline import TimelineEvent

RECORD_TYPES = {
    "technical": (
        AssetTechnicalAttribute,
        AssetTechnicalAttributeResponse,
        "attribute_key",
    ),
    "conditions": (AssetCondition, AssetConditionResponse, "condition_date"),
    "inspections": (Inspection, InspectionResponse, "inspection_date"),
    "repairs": (Repair, RepairResponse, "repair_date"),
    "maintenance": (MaintenanceRecord, MaintenanceRecordResponse, "maintenance_date"),
}


def require_asset(db: Session, asset_id: UUID) -> None:
    if db.scalar(select(Asset.id).where(Asset.id == asset_id)) is None:
        raise HTTPException(status_code=404, detail="Asset not found")


def list_records(db: Session, asset_id: UUID, kind: str):
    model, schema, sort_key = RECORD_TYPES[kind]
    primary_order = getattr(model, sort_key)
    if kind != "technical":
        primary_order = primary_order.desc()
    query = (
        select(model)
        .where(model.asset_id == asset_id)
        .options(selectinload(model.source))
        .order_by(primary_order, model.created_at.desc(), model.id.desc())
    )
    return [schema.model_validate(record) for record in db.scalars(query)]


def current_condition(db: Session, asset_id: UUID) -> AssetConditionResponse | None:
    record = db.scalar(
        select(AssetCondition)
        .where(
            AssetCondition.asset_id == asset_id,
            AssetCondition.verification_status == "VERIFIED",
        )
        .options(selectinload(AssetCondition.source))
        .order_by(
            AssetCondition.condition_date.desc(),
            AssetCondition.created_at.desc(),
            AssetCondition.id.desc(),
        )
        .limit(1)
    )
    return AssetConditionResponse.model_validate(record) if record else None


def timeline(db: Session, asset_id: UUID) -> list[TimelineEvent]:
    events = []
    config = [
        ("conditions", "CONDITION", "condition_date", "condition_status", "summary"),
        ("inspections", "INSPECTION", "inspection_date", "inspection_type", "summary"),
        ("repairs", "REPAIR", "repair_date", "repair_type", "repair_description"),
        (
            "maintenance",
            "MAINTENANCE",
            "maintenance_date",
            "maintenance_type",
            "description",
        ),
    ]
    for kind, event_type, date_key, title_key, summary_key in config:
        for record in list_records(db, asset_id, kind):
            events.append(
                TimelineEvent(
                    event_type=event_type,
                    event_date=getattr(record, date_key),
                    title=getattr(record, title_key) or event_type.title(),
                    summary=getattr(record, summary_key),
                    record_id=record.id,
                    asset_id=record.asset_id,
                    source_id=record.source_id,
                    source=record.source,
                    verification_status=record.verification_status,
                )
            )
    return sorted(
        events,
        key=lambda event: (event.event_date, event.event_type, str(event.record_id)),
        reverse=True,
    )
