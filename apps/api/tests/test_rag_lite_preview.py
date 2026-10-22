import io

from pypdf import PdfWriter
from test_rag_lite_query import rag as rag  # noqa: PLC0414 -- imported pytest fixture

from app.core.config import settings
from app.services.rag_lite.indexer import atomic_json, build_index, digest


def test_live_coverage_excludes_revoked_missing_and_changed_originals(rag, monkeypatch):
    client, body, _, doc, storage, _, _ = rag
    url = f"/api/v1/experimental/rag-lite/coverage?reservoir_id={body['reservoir_id']}"
    result = client.get(url)
    assert result.headers["cache-control"] == "no-store"
    assert result.json() == {
        "authorized_documents": 1,
        "searchable_documents": 1,
        "image_only_documents": 0,
        "unavailable_documents": 0,
        "searchable_pages": 1,
        "indexed_chunks": 1,
    }
    storage.store(doc.storage_key, b"changed bytes")
    changed = client.get(url).json()
    assert (
        changed["searchable_documents"] == 0 and changed["unavailable_documents"] == 1
    )
    assert str(storage.root) not in str(changed)
    monkeypatch.setattr(settings, "rag_lite_allowlist_path", None)
    assert client.get(url).json()["authorized_documents"] == 0


def test_coverage_blank_scan_and_reservoir_boundary(rag):
    client, body, _, doc, storage, _, empty = rag
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    data = buf.getvalue()
    doc.checksum_sha256 = digest(data)
    storage.store(doc.storage_key, data)
    atomic_json(
        settings.rag_lite_allowlist_path,
        {
            "version": 1,
            "authorization": "Synthetic only",
            "documents": [
                {"document_id": str(doc.id), "checksum_sha256": doc.checksum_sha256}
            ],
        },
    )
    build_index(
        [doc],
        storage,
        settings.rag_lite_index_dir,
        {str(doc.id): doc.checksum_sha256},
        {},
    )
    base = "/api/v1/experimental/rag-lite/coverage?reservoir_id="
    result = client.get(base + body["reservoir_id"]).json()
    assert result["image_only_documents"] == 1 and result["searchable_documents"] == 0
    assert client.get(base + str(empty.id)).json()["authorized_documents"] == 0


def test_demo_labels_are_actual_fields_and_preview_remains_disabled(rag, monkeypatch):
    client, body, _, _, _, record, _ = rag
    result = client.get(
        "/api/v1/experimental/rag-lite/demo-questions",
        params={"reservoir_id": body["reservoir_id"], "asset_id": body["asset_id"]},
    ).json()
    assert result[0] == {
        "question": record.attribute_label,
        "attribute_key": record.attribute_key,
        "attribute_label": record.attribute_label,
    }
    monkeypatch.setattr(settings, "rag_lite_enabled", False)
    assert (
        client.get(
            "/api/v1/experimental/rag-lite/coverage",
            params={"reservoir_id": body["reservoir_id"]},
        ).status_code
        == 404
    )
