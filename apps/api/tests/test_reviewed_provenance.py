import json
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services.reviewed_provenance import technical_provenance


class Record:
    id = "record"
    source = SimpleNamespace(source_code="RS-S")

    def model_dump(self, **kwargs):
        return {"id": "record", "value_number": 28}


@pytest.mark.parametrize("change", ["none", "value", "source", "missing", "malformed"])
def test_sidecar_requires_exact_record_and_source(tmp_path, monkeypatch, change):
    path = tmp_path / "provenance.json"
    monkeypatch.setattr(settings, "reviewed_provenance_path", path)
    entry = {
        "record": {"id": "record", "value_number": 28},
        "provenance": {
            "verification_level": "L2",
            "source_code": "RS-S",
            "evidence_id": "E1",
            "source_locator": "PDF:p2",
            "authority": "SUPPORTING",
            "reviewer": "TEST",
            "reviewed_at": "2026-10-13T00:00:00Z",
        },
    }
    if change == "value":
        entry["record"]["value_number"] = 29
    if change == "source":
        entry["provenance"]["source_code"] = "OTHER"
    if change != "missing":
        path.write_text(
            "invalid"
            if change == "malformed"
            else json.dumps({"version": 1, "records": {"record": entry}})
        )
    result = technical_provenance(Record())
    assert (result is not None) == (change == "none")
