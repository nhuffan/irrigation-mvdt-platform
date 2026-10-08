"""Synthetic conversion fixtures; not case-study evidence."""

from uuid import uuid4

import pytest

from scripts.prepare_initial_research_batch import build_batch


def fixture(raw_date):
    targets = [
        {
            "target_asset_code": "RS-A",
            "category": "RS-CAT-DAM",
            "verification_status": "UNVERIFIED",
            "in_scope": "true",
            "requires_3d": "false",
        }
    ]
    sources = [
        {
            "source_code": "RS-S",
            "source_type": "AS_BUILT",
            "title": "Test",
            "source_date": raw_date,
            "source_owner": "",
            "authority_level": "",
            "verification_status": "UNVERIFIED",
            "related_asset_codes": "RS-A",
            "file_expected": "true",
            "file_available": "true",
            "evidence_reference": "TEST",
            "notes": "TEST",
        }
    ]
    maim = [{"category": "RS-CAT-DAM", "required": "false"}]
    ids = {
        (kind, code): str(uuid4())
        for kind, code in [("asset_categories", "RS-CAT-DAM"), ("data_sources", "RS-S")]
    }
    return targets, sources, maim, str(uuid4()), "TEST structural reviewer", ids


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1999-09", None),
        ("2002", None),
        ("2024-08/2025-12", None),
        ("", None),
        ("2002-03-04", "2002-03-04"),
    ],
)
def test_dates_and_no_invented_records(raw, expected):
    batch = build_batch(*fixture(raw))
    assert set(batch["records"]) == {"asset_categories", "data_sources"}
    source = batch["records"]["data_sources"][0]
    assert source["source_date"] == expected
    assert source["file_name"] is None
    assert source["source_owner"] is None
    assert source["verification_status"] == "UNVERIFIED"
    assert "file_available" not in source
    assert source["notes"]


def test_rejects_unknown_asset_link_and_verified_source():
    values = fixture("")
    values[1][0]["related_asset_codes"] = "RS-UNKNOWN"
    with pytest.raises(ValueError, match="unknown candidate"):
        build_batch(*values)
    values[1][0]["related_asset_codes"] = "RS-A"
    values[1][0]["verification_status"] = "VERIFIED"
    with pytest.raises(ValueError, match="UNVERIFIED"):
        build_batch(*values)


def test_reuses_supplied_ids_and_rejects_invalid_full_date():
    values = fixture("2024-02-30")
    with pytest.raises(ValueError):
        build_batch(*values)
    values[1][0]["source_date"] = ""
    assert build_batch(*values) == build_batch(*values)


def test_scope_reader_accepts_excel_utf8_bom(tmp_path):
    from scripts.prepare_empirical_scope import read_rows

    path = tmp_path / "targets.csv"
    path.write_text("target_asset_code,in_scope\nRS-A,true\n", encoding="utf-8-sig")
    assert read_rows(path) == [{"target_asset_code": "RS-A", "in_scope": "true"}]
