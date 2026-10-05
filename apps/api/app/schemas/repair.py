from datetime import date

from app.schemas.om_common import RecordResponse


class RepairResponse(RecordResponse):
    repair_date: date
    repair_type: str | None
    problem_description: str | None
    repair_description: str
    result: str | None
    responsible_unit: str | None
