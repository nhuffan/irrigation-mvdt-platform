from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

VerificationStatus = Literal["UNVERIFIED", "PARTIALLY_VERIFIED", "VERIFIED", "REJECTED"]


class DataSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reservoir_id: UUID
    source_code: str
    source_type: str
    title: str
    file_name: str | None
    source_date: date | None
    source_owner: str | None
    authority_level: str | None
    verification_status: VerificationStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
