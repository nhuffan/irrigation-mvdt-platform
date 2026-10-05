from datetime import date

from app.schemas.om_common import RecordResponse


class MaintenanceRecordResponse(RecordResponse):
    maintenance_date: date
    maintenance_type: str | None
    description: str
    result: str | None
    responsible_unit: str | None
