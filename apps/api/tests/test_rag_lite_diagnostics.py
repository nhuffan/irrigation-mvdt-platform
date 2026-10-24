"""Synthetic diagnostics and source-checked field-label regressions."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from test_rag_lite_query import URL
from test_rag_lite_query import rag as rag  # noqa: PLC0414 -- imported pytest fixture

from app.core.config import settings
from app.services.rag_lite.indexer import atomic_json, load_index
from app.services.rag_lite.retriever import attribute_matches, tokens


def coverage(client, body, asset_id=None):
    return client.get(
        "/api/v1/experimental/rag-lite/coverage",
        params={
            "reservoir_id": body["reservoir_id"],
            "asset_id": asset_id or body["asset_id"],
        },
    )


def test_selected_coverage_is_direct_and_metadata_unknown(rag):
    client, body, assets, *_ = rag
    response = coverage(client, body)
    assert response.status_code == 200
    data = response.json()
    assert data["diagnostics"]["reviewed_attributes"] == 1
    assert data["diagnostics"]["direct_documents"] == 1
    assert data["searchable_documents"] == 1
    assert "SOURCE_METADATA_UNKNOWN" in data["diagnostics"]["reason_codes"]
    other = coverage(client, body, str(assets[1].id)).json()
    assert other["authorized_documents"] == 0
    assert set(other["diagnostics"]["reason_codes"]) == {
        "NO_DIRECT_DOCUMENT",
        "NO_REVIEWED_ATTRIBUTE",
    }
    assert coverage(client, body, str(uuid4())).status_code == 404


@pytest.mark.parametrize(
    "failure,expected",
    [
        ("revoked", "NOT_AUTHORIZED"),
        ("missing", "DOCUMENT_MISSING"),
        ("changed", "DOCUMENT_INVALID"),
        ("stale", "INDEX_INVALID"),
        ("low_text", "EXTRACTION_LIMITED"),
        ("image", "IMAGE_ONLY"),
    ],
)
def test_document_failure_reasons(rag, monkeypatch, failure, expected):
    client, body, _, doc, storage, *_ = rag
    path = settings.rag_lite_index_dir / f"{doc.id}.json"
    if failure == "revoked":
        monkeypatch.setattr(settings, "rag_lite_allowlist_path", None)
    elif failure == "missing":
        storage.path(doc.storage_key).unlink()
    elif failure == "changed":
        storage.store(doc.storage_key, b"changed original")
    else:
        index = load_index(path, doc)
        if failure == "stale":
            index["version"] = "stale synthetic version"
        else:
            index["chunks"] = []
            index["coverage"] = [
                {
                    "page": 1,
                    "characters": 0 if failure == "image" else 12,
                    "indexed": False,
                }
            ]
        atomic_json(path, index)
    data = coverage(client, body).json()
    assert data["searchable_documents"] == 0
    assert expected in data["diagnostics"]["reason_codes"]
    assert data["diagnostics"]["unscoped_documents"] == 0
    assert "NO_SCOPED_PASSAGE" not in data["diagnostics"]["reason_codes"]
    result = client.post(
        URL, json={**body, "query_type": "document", "question": "synthetic inspection"}
    ).json()
    assert not result["citations"]
    assert expected in result["reason_codes"]
    assert str(storage.root) not in str(data) + str(result)


def test_no_match_and_refusal_are_distinct(rag):
    client, body, *_ = rag
    result = client.post(
        URL, json={**body, "query_type": "document", "question": "quantum banana"}
    ).json()
    assert result["reason_codes"] == ["NO_MATCH"]
    assert client.post(URL, json={**body, "question": "current condition"}).json()[
        "reason_codes"
    ] == ["OUT_OF_SCOPE"]


def test_suggestions_require_an_actual_value(rag):
    client, body, _, _, _, record, _ = rag
    record.value_number = None
    record.value_text = " "
    assert (
        client.get(
            "/api/v1/experimental/rag-lite/demo-questions",
            params={"asset_id": body["asset_id"], "reservoir_id": body["reservoir_id"]},
        ).json()
        == []
    )


@pytest.mark.parametrize(
    "question,expected",
    [
        ("áp suất thử nghiệm", False),
        ("áp suất thiết kế", True),
        ("design pressure", True),
        ("áp suất hiện tại", False),
        ("áp suất 270", False),
        ("áp suất 200 bar", True),
    ],
)
def test_design_label_does_not_answer_test_pressure(question, expected):
    # Actual RS-SRC-018 label/value, source-checked against original manual.
    record = SimpleNamespace(
        attribute_key="reported_gate_cylinder_design_pressure",
        attribute_label="Áp suất thiết kế xi lanh cửa van tràn theo sổ tay",
        value_number=200.0,
        value_text=None,
        unit="bar",
    )
    assert attribute_matches(record, question, tokens(question)) is expected


def test_partial_sql_overlap_falls_through(rag):
    client, body, _, _, _, record, _ = rag
    record.attribute_key = "reported_gate_cylinder_design_pressure"
    record.attribute_label = "Áp suất thiết kế xi lanh cửa van tràn theo sổ tay"
    record.value_number = 200
    assert not client.post(URL, json={**body, "question": "áp suất thử nghiệm"}).json()[
        "citations"
    ]
    assert (
        client.post(URL, json={**body, "question": "áp suất thiết kế"}).json()[
            "citations"
        ][0]["value_number"]
        == 200
    )


def test_numeric_value_refines_field_without_selecting_by_number_alone():
    record = SimpleNamespace(
        attribute_key="reported_stroke",
        attribute_label="Hành trình xi lanh",
        value_number=4650.0,
        value_text=None,
        unit="mm",
    )
    assert attribute_matches(record, "hành trình 4650", tokens("hành trình 4650"))
    assert not attribute_matches(record, "4650", tokens("4650"))
    record.attribute_label = "tam"
    assert not attribute_matches(record, "tâm", tokens("tâm"))


def test_partial_search_retains_valid_citations(rag, domain):
    import io
    import json

    from pypdf import PdfReader, PdfWriter

    from app.models.media import Document
    from app.services.rag_lite.indexer import digest

    client, body, _, doc, storage, _, _ = rag
    writer = PdfWriter(
        clone_from=PdfReader(io.BytesIO(storage.path(doc.storage_key).read_bytes()))
    )
    writer.add_metadata({"/Title": "Second synthetic original"})
    output = io.BytesIO()
    writer.write(output)
    data = output.getvalue()
    storage.store("second.pdf", data)
    second_id = uuid4()
    allowlist = json.loads(settings.rag_lite_allowlist_path.read_text())
    allowlist["documents"].append(
        {"document_id": str(second_id), "checksum_sha256": digest(data)}
    )
    atomic_json(settings.rag_lite_allowlist_path, allowlist)
    db = domain[1]
    db.add(
        Document(
            id=second_id,
            source_id=doc.source_id,
            document_code=f"T-{uuid4()}",
            original_file_name="synthetic missing index.pdf",
            storage_key="second.pdf",
            mime_type=doc.mime_type,
            file_size=len(data),
            checksum_sha256=digest(data),
        )
    )
    db.flush()
    data = coverage(client, body).json()
    assert data["searchable_documents"] == 1
    assert data["diagnostics"]["invalid_indexes"] == 1
    result = client.post(
        URL, json={**body, "query_type": "document", "question": "synthetic inspection"}
    ).json()
    assert result["citations"] and result["reason_codes"] == ["INDEX_INVALID"]
    assert all(c["document_id"] == str(doc.id) for c in result["citations"])


def test_numeric_query_cannot_match_the_decimal_zero_fragment():
    record = SimpleNamespace(
        attribute_key="reported_stroke",
        attribute_label="Hành trình xi lanh",
        value_number=4650.0,
        value_text=None,
        unit="mm",
    )
    assert not attribute_matches(record, "hành trình 0", tokens("hành trình 0"))
    assert not attribute_matches(
        record, "hành trình 4650.1", tokens("hành trình 4650.1")
    )
    assert attribute_matches(record, "hành trình 4650.0", tokens("hành trình 4650.0"))


def test_valid_shared_original_with_no_exact_scoped_passage_is_available(rag):
    import json

    from app.services.rag_lite.sections import extract_sections

    client, body, assets, doc, storage, *_ = rag
    index = extract_sections(
        doc,
        storage.path(doc.storage_key).read_bytes(),
        [
            {
                "page": 1,
                "start": "DEVELOPMENT ONLY - SYNTHETIC DOCUMENT",
                "asset_ids": [str(assets[1].id)],
            }
        ],
        "Synthetic extraction scope review; no engineering approval",
    )
    atomic_json(settings.rag_lite_index_dir / f"{doc.id}.json", index)
    allow = json.loads(settings.rag_lite_allowlist_path.read_text())
    allow["documents"][0]["scope_sha256"] = index["scope_sha256"]
    atomic_json(settings.rag_lite_allowlist_path, allow)

    selected = coverage(client, body).json()
    assert selected["authorized_documents"] == 1
    assert selected["searchable_documents"] == 0
    assert selected["image_only_documents"] == 0
    assert selected["unavailable_documents"] == 0
    assert selected["diagnostics"]["reviewed_attributes"] == 1
    assert selected["diagnostics"]["unscoped_documents"] == 1
    assert "NO_SCOPED_PASSAGE" in selected["diagnostics"]["reason_codes"]

    request = {**body, "query_type": "document", "question": "synthetic inspection"}
    scoped = client.post(URL, json=request).json()
    assert scoped["status"] == "NOT_ENOUGH_EVIDENCE"
    assert scoped["reason_codes"] == ["NO_SCOPED_PASSAGE"]
    assert not scoped["citations"]
    assert client.post(URL, json=body).json()["citations"][0]["kind"] == (
        "technical_attribute"
    )
    corpus = client.post(
        URL, json={**request, "asset_id": None, "all_authorized_docs": True}
    ).json()
    assert corpus["citations"] and all(
        c["asset_id"] is None for c in corpus["citations"]
    )
    assert "NO_SCOPED_PASSAGE" not in corpus["reason_codes"]
    corpus_coverage = client.get(
        "/api/v1/experimental/rag-lite/coverage",
        params={"reservoir_id": body["reservoir_id"]},
    ).json()
    assert corpus_coverage["searchable_documents"] == 1
    assert corpus_coverage["unavailable_documents"] == 0

    atomic_json(settings.rag_lite_allowlist_path, {**allow, "documents": []})
    revoked = client.post(URL, json=request).json()
    assert revoked["reason_codes"] == ["NOT_AUTHORIZED"]
    assert coverage(client, body).json()["diagnostics"]["unscoped_documents"] == 0
