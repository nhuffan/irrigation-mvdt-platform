from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.data_source import DataSourceResponse, VerificationStatus


class TimelineEvent(BaseModel):
    event_type: Literal["CONDITION", "INSPECTION", "REPAIR", "MAINTENANCE"]
    event_date: date
    title: str
    summary: str | None
    record_id: UUID
    asset_id: UUID
    source_id: UUID | None
    source: DataSourceResponse | None
    verification_status: VerificationStatus
