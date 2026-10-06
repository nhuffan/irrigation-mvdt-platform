from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.data_source import DataSourceResponse


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_id: UUID
    document_code: str
    original_file_name: str
    mime_type: str | None
    file_size: int | None
    checksum_sha256: str | None
    page_count: int | None
    uploaded_at: datetime
    source: DataSourceResponse


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reservoir_id: UUID
    source_id: UUID | None
    model_code: str
    name: str
    model_type: str
    format: str
    coordinate_mode: str
    longitude: float | None
    latitude: float | None
    height: float | None
    heading: float
    pitch: float
    roll: float
    scale: float
    verification_status: str
    source: DataSourceResponse | None


class ModelAssetLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    model_id: UUID
    asset_id: UUID
    reservoir_id: UUID
    object_key: str
    object_name: str | None
    verification_status: str
