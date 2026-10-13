from typing import Literal

from pydantic import BaseModel

from app.schemas.om_common import RecordResponse


class ReviewedProvenance(BaseModel):
    verification_level: Literal["L0", "L1", "L2", "L3"]
    source_code: str
    evidence_id: str
    source_locator: str
    authority: str
    reviewer: str
    reviewed_at: str


class AssetTechnicalAttributeResponse(RecordResponse):
    attribute_key: str
    attribute_label: str
    value_text: str | None
    value_number: float | None
    unit: str | None
    reviewed_provenance: ReviewedProvenance | None = None
