from app.schemas.om_common import RecordResponse


class AssetTechnicalAttributeResponse(RecordResponse):
    attribute_key: str
    attribute_label: str
    value_text: str | None
    value_number: float | None
    unit: str | None
