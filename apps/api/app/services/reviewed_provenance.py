"""Optional reviewed sidecar; missing/stale metadata never implies verification."""

import json

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.technical_attribute import ReviewedProvenance

BINDING_FIELDS = (
    "id",
    "asset_id",
    "source_id",
    "attribute_key",
    "attribute_label",
    "value_number",
    "value_text",
    "unit",
    "verification_status",
)


def technical_provenance(record):
    path = (
        settings.reviewed_provenance_path
        or settings.storage_root / "reviewed_provenance.json"
    )
    try:
        bundle = json.loads(path.read_text())
        if bundle.get("version") != 1:
            return None
        entry = bundle["records"][str(record.id)]
        actual = record.model_dump(mode="json", include=set(BINDING_FIELDS))
        if entry["record"] != actual or not record.source:
            return None
        provenance = ReviewedProvenance.model_validate(entry["provenance"])
        if provenance.source_code != record.source.source_code:
            return None
        return provenance
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ValidationError):
        return None
