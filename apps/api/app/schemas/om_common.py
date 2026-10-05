from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.data_source import DataSourceResponse, VerificationStatus


class RecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: UUID
    source_id: UUID | None
    source: DataSourceResponse | None
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime
