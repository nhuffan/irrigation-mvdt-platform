"""Synthetic page traversal; original fixture bytes are indexed, never invented hits."""

import io

import pytest
from pypdf import PdfReader, PdfWriter
from test_rag_lite_query import URL
from test_rag_lite_query import rag as rag  # noqa: PLC0414 -- imported pytest fixture

from app.core.config import settings
from app.services.rag_lite.indexer import atomic_json, build_index, digest


@pytest.fixture
def multi_page(rag):
    client, body, _, doc, storage, _, _ = rag
    reader = PdfReader(io.BytesIO(storage.path(doc.storage_key).read_bytes()))
    writer = PdfWriter()
    for _ in range(11):
        writer.add_page(reader.pages[0])
    output = io.BytesIO()
    writer.write(output)
    data = output.getvalue()
    doc.checksum_sha256 = digest(data)
    storage.store(doc.storage_key, data)
    allow = {str(doc.id): doc.checksum_sha256}
    atomic_json(
        settings.rag_lite_allowlist_path,
        {
            "version": 1,
            "authorization": "Synthetic pagination fixture only",
            "documents": [
                {"document_id": str(doc.id), "checksum_sha256": doc.checksum_sha256}
            ],
        },
    )
    build_index([doc], storage, settings.rag_lite_index_dir, allow, {})
    return (
        client,
        {**body, "question": "synthetic inspection", "query_type": "document"},
        rag,
    )


def test_every_ranked_passage_is_reachable_without_duplicates(multi_page):
    client, query, _ = multi_page
    legacy = client.post(URL, json=query).json()
    assert len(legacy["citations"]) == 5  # Existing top_k contract is retained.
    ids, pages = [], []
    for page, expected_count in [(1, 5), (2, 5), (3, 1)]:
        result = client.post(URL, json={**query, "page": page, "page_size": 5}).json()
        assert result["status"] == "RETRIEVAL_ONLY"
        assert result["pagination"] == {
            "page": page,
            "page_size": 5,
            "total_results": 11,
            "total_pages": 3,
        }
        assert len(result["citations"]) == expected_count
        ids += [c["citation_id"] for c in result["citations"]]
        pages += [c["page"] for c in result["citations"]]
    assert len(set(ids)) == 11 and pages == list(range(1, 12))
    assert ids[:5] == [c["citation_id"] for c in legacy["citations"]]
    last = client.post(URL, json={**query, "page": 100, "page_size": 5}).json()
    assert last["pagination"]["page"] == 3
    assert [c["page"] for c in last["citations"]] == [11]


def test_each_page_revalidates_authorization_and_scope(multi_page, monkeypatch):
    client, query, rag_data = multi_page
    other = rag_data[2][1]
    scoped = client.post(
        URL, json={**query, "asset_id": str(other.id), "page": 2, "page_size": 5}
    ).json()
    assert scoped["pagination"]["total_results"] == 0 and not scoped["citations"]
    corpus = client.post(
        URL,
        json={
            **query,
            "asset_id": None,
            "all_authorized_docs": True,
            "page": 2,
            "page_size": 5,
        },
    ).json()
    assert corpus["pagination"]["total_results"] == 11
    assert all(c["asset_id"] is None for c in corpus["citations"])
    monkeypatch.setattr(settings, "rag_lite_allowlist_path", None)
    revoked = client.post(URL, json={**query, "page": 2, "page_size": 5}).json()
    assert revoked["pagination"]["total_results"] == 0 and not revoked["citations"]
    assert "NOT_AUTHORIZED" in revoked["reason_codes"]


def test_each_page_checks_current_original_bytes(multi_page):
    client, query, rag_data = multi_page
    first = client.post(URL, json={**query, "page": 1, "page_size": 5}).json()
    assert first["citations"]
    rag_data[4].store(rag_data[3].storage_key, b"changed original")
    stale = client.post(URL, json={**query, "page": 2, "page_size": 5}).json()
    assert not stale["citations"] and stale["pagination"]["total_results"] == 0
    assert "DOCUMENT_INVALID" in stale["reason_codes"]


@pytest.mark.parametrize(
    "patch",
    [
        {"page": 0, "page_size": 5},
        {"page": 1, "page_size": 0},
        {"page": 1, "page_size": 21},
        {"page": 10001, "page_size": 5},
        {"page": 1},
        {"page_size": 5},
        {"page": 1, "page_size": 5, "mode": "grounded_answer"},
    ],
)
def test_pagination_input_is_bounded_and_explicit(rag, patch):
    client, body, *_ = rag
    assert client.post(URL, json={**body, **patch}).status_code == 422


def test_exact_sql_uses_same_page_metadata(rag):
    client, body, *_ = rag
    value = client.post(URL, json={**body, "page": 2, "page_size": 5}).json()
    assert value["pagination"] == {
        "page": 1,
        "page_size": 5,
        "total_results": 1,
        "total_pages": 1,
    }
    assert value["citations"][0]["value_number"] == 270
