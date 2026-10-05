from datetime import date

from app.schemas.om_common import RecordResponse


class AssetConditionResponse(RecordResponse):
    condition_date: date
    condition_status: str
    summary: str | None
    defect_description: str | None
    recommended_action: str | None
