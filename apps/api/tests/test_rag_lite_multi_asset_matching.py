"""Synthetic matching checks only; original-source evaluation is a separate cohort."""

from types import SimpleNamespace

import pytest
from test_rag_lite_query import URL
from test_rag_lite_query import rag as rag  # noqa: PLC0414

from app.services.rag_lite.retriever import (
    attribute_matches,
    rank_document_chunks,
    tokens,
)
from app.services.rag_lite.vocabulary import numeric_literals, scoped_question


def field(key, label, number=None, unit="m", text=None):
    return SimpleNamespace(
        attribute_key=key,
        attribute_label=label,
        value_number=number,
        value_text=text,
        unit=unit,
    )


@pytest.mark.parametrize(
    "question,record",
    [
        (
            "discharge 93m3/s",
            field(
                "reported_discharge",
                "Lưu lượng theo SIWRR 2010 (C01/C02 tại MNDBT; C03 thiết kế)",
                93,
                "m3/s",
            ),
        ),
        (
            "sill elevation 15,75m",
            field(
                "reported_sill_elevation",
                "Cao trình ngưỡng theo SIWRR 2010 (datum UNKNOWN)",
                15.75,
            ),
        ),
        (
            "opening width 3m",
            field("reported_opening_width", "Bề rộng mỗi lỗ/cửa theo SIWRR 2010", 3),
        ),
        (
            "height per opening 4m",
            field("reported_opening_height", "Chiều cao mỗi lỗ/cửa theo SIWRR 2010", 4),
        ),
        (
            "number of openings",
            field(
                "reported_n",
                "Số lỗ/cửa theo ký hiệu nguồn SIWRR 2010 (không chứng nhận lá van)",
                3,
                "count",
            ),
        ),
        (
            "water tank capacity 1500L",
            field(
                "reported_water_tank_capacity",
                "Dung tích bồn nước theo hồ sơ (không xác nhận hiện trạng)",
                1500,
                "L",
            ),
        ),
        (
            "main door material",
            field(
                "reported_main_door_material",
                "Vật liệu cửa chính theo hồ sơ",
                unit="text",
                text="Nhôm kính",
            ),
        ),
        (
            "roof structure",
            field(
                "reported_roof_material",
                "Kết cấu mái theo hồ sơ (không xác nhận hiện trạng)",
                unit="text",
                text="Ngói",
            ),
        ),
        (
            "roof gutter structure",
            field(
                "reported_roof_gutter_structure",
                "Kết cấu sê nô theo hồ sơ",
                unit="text",
                text="BTCT",
            ),
        ),
    ],
)
def test_natural_field_concepts_preserve_actual_values_and_units(question, record):
    assert attribute_matches(record, question, tokens(question))


@pytest.mark.parametrize(
    "question",
    [
        "water tank capacity 150L",
        "water tank capacity 1.5m3",
        "water tank capacity 1500m3",
        "water tank capacity forecast",
    ],
)
def test_aliases_do_not_convert_units_or_drop_numeric_or_meaningful_qualifiers(
    question,
):
    record = field(
        "reported_water_tank_capacity", "Dung tích bồn nước theo hồ sơ", 1500, "L"
    )
    assert not attribute_matches(record, question, tokens(question))


def test_opening_dimension_concepts_do_not_exchange_width_and_height():
    record = field("reported_opening_width", "Bề rộng mỗi lỗ/cửa theo SIWRR 2010", 3)
    assert not attribute_matches(
        record, "opening height 3m", tokens("opening height 3m")
    )
    assert not attribute_matches(
        record, "certified gate count", tokens("certified gate count")
    )


def test_unit_typography_and_adjacency_keep_the_same_literal_number():
    assert numeric_literals("12,8m3/s") == numeric_literals("12.8 m³/s") == {"12.8"}
    assert numeric_literals("1500L") == {"1500"}
    assert numeric_literals("12,800 m3/s") == {"12,800"}


def rank(question, passages):
    document = SimpleNamespace(id="synthetic")
    candidates = [
        (document, {"page": i, "offset": 0, "text": passage}, tokens(passage))
        for i, passage in enumerate(passages, 1)
    ]
    return rank_document_chunks(candidates, question, tokens(question))


@pytest.mark.parametrize("question", ["lưu lượng 93m3/s", "discharge 93 m³/s"])
def test_attested_split_text_alias_keeps_original_excerpt_and_literal_units(question):
    passage = "Cống Số 1. Cao trình ngưỡng +13m, lư u lượng tại mực nước bình thường là 93m3/s."
    rows = rank(question, [passage, "Công suất điện; chất lượng vật liệu 93m3/s."])
    assert [row[3]["page"] for row in rows] == [1]
    assert rows[0][3]["text"] == passage


def test_document_aliases_keep_outside_accents_numbers_and_concepts():
    passages = ["Cao trình ngưỡng +15,75 m; dày.", "Cao trình ngưỡng +15,75 m; đáy."]
    assert [row[3]["page"] for row in rank("sill elevation đáy 15.75m", passages)] == [
        2
    ]
    assert not rank("sill elevation 1.575m", passages)
    assert not rank("opening width", ["Kích thước mỗi cửa 3*4 m."])
    assert not rank("main door material", ["Vật liệu nhôm của cửa sổ."])


def assets():
    return [
        SimpleNamespace(
            id=str(i), asset_code=f"SYNTHETIC-C0{i}", name=f"Cống số {i} — Kênh {i}"
        )
        for i in [1, 2, 3]
    ]


@pytest.mark.parametrize(
    "question",
    [
        "Intake 1 discharge",
        "Intake No. 1 discharge",
        "Cống số 1 lưu lượng",
        "C01 discharge",
        "synthetic-c01 discharge",
    ],
)
def test_selected_label_numbers_are_scope_context_not_value_constraints(question):
    component = assets()
    cleaned, mismatch = scoped_question(question, component[0], component)
    assert not mismatch
    assert numeric_literals(cleaned) == set()
    record = field("reported_discharge", "Lưu lượng theo SIWRR 2010", 93, "m3/s")
    assert attribute_matches(record, cleaned, tokens(cleaned))


@pytest.mark.parametrize(
    "question",
    [
        "Intake 2 discharge",
        "Intake No. 2 discharge",
        "Cống số 3 lưu lượng",
        "C02 discharge",
        "SYNTHETIC-C03 discharge",
    ],
)
def test_unambiguous_other_component_names_fail_closed(question):
    component = assets()
    assert scoped_question(question, component[0], component)[1]


def test_shared_names_are_not_resolved_to_an_arbitrary_asset():
    component = assets()
    component[1].name = component[0].name
    cleaned, mismatch = scoped_question("Cống số 1 discharge", component[0], component)
    assert not mismatch and "1" in numeric_literals(cleaned)


def test_api_selected_alias_free_text_and_cross_component_rejection(rag):
    client, body, component, _, _, record, _ = rag
    component[0].name, component[0].asset_code = (
        "Cống số 1 — Kênh Đông",
        "SYNTHETIC-C01",
    )
    component[1].name, component[1].asset_code = "Cống số 2 — Kênh Tây", "SYNTHETIC-C02"
    record.attribute_key, record.attribute_label = (
        "reported_discharge",
        "Lưu lượng theo SIWRR 2010",
    )
    record.value_number, record.unit = 93, "m3/s"
    # The shared fixture session flushes during the API's existing DB reads.
    result = client.post(URL, json={**body, "question": "lưu lượng cống số 1"}).json()
    assert result["citations"][0]["record_id"] == str(record.id)
    assert result["citations"][0]["value_number"] == 93
    result = client.post(URL, json={**body, "question": "Intake 2 discharge"}).json()
    assert not result["citations"] and "SCOPE_MISMATCH" in result["reason_codes"]


def test_longest_component_name_does_not_also_select_its_parent():
    component = assets()
    parent = SimpleNamespace(
        id="parent", asset_code="SYNTHETIC-INTAKE", name="Công trình lấy nước"
    )
    for question in (
        "Intake 1 discharge",
        "Intake No. 1 discharge",
        "Cống số 1 lưu lượng",
    ):
        cleaned, mismatch = scoped_question(
            question, component[0], [parent, *component]
        )
        assert not mismatch and numeric_literals(cleaned) == set()
    assert scoped_question("Intake 2 discharge", component[0], [parent, *component])[1]
    assert scoped_question("Intake 1 discharge", parent, [parent, *component])[1]
    assert scoped_question(
        "Intake 1 and Intake 2 discharge", component[0], [parent, *component]
    )[1]


def test_selected_asset_noun_keeps_the_full_engineering_concept():
    dam = SimpleNamespace(id="dam", asset_code="SYNTHETIC-DAM", name="Đập / Dam")
    cleaned, mismatch = scoped_question("vật liệu đập", dam, [dam])
    assert not mismatch and cleaned == "vật liệu đập"
    rows = rank(
        cleaned, ["Tài liệu vật liệu khác.", "Main Dam Earthfilll crest table."]
    )
    assert [row[3]["page"] for row in rows] == [2]
