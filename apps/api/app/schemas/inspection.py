from datetime import date

from app.schemas.om_common import RecordResponse


class InspectionResponse(RecordResponse):
    inspection_date: date
    inspection_type: str | None
    inspector: str | None
    summary: str | None
    observation: str | None
    condition_status: str | None
    recommended_action: str | None
