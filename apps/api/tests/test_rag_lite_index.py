import io
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pypdf import PdfWriter

from app.services.rag_lite.indexer import (
    MAX_BYTES,
    atomic_json,
    build_index,
    chunks_for_page,
    digest,
    extract,
    load_allowlist,
    load_index,
    read_pdf,
)
from app.storage.local import LocalStorage
from scripts.seed_media import demo_pdf


def document(data):
    return SimpleNamespace(
        id=uuid4(),
        source_id=uuid4(),
        checksum_sha256=digest(data),
        storage_key="test.pdf",
    )


@pytest.mark.parametrize(
    "key", ["../private", "/etc/passwd", "x/../../outside", "..\\private", ""]
)
def test_no_path_traversal(tmp_path, key):
    doc = document(b"x")
    doc.storage_key = key
    with pytest.raises(ValueError):
        read_pdf(LocalStorage(tmp_path), doc)


def test_symlink_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "escape").symlink_to(tmp_path, target_is_directory=True)
    doc = document(b"x")
    doc.storage_key = "escape/file"
    with pytest.raises(ValueError):
        read_pdf(LocalStorage(root), doc)


def test_deterministic_page_chunks():
    result = chunks_for_page("doc", "hash", 7, "original text " * 400)
    assert result == chunks_for_page("doc", "hash", 7, "original text " * 400)
    assert len(result) > 1 and all(
        c["page"] == 7 and len(c["text"]) <= 1400 for c in result
    )
    assert (
        result[0]["chunk_id"]
        != chunks_for_page("doc", "hash", 8, "original text " * 400)[0]["chunk_id"]
    )
    assert chunks_for_page("doc", "hash", 1, " \n ") == []


def test_blank_scan_and_pdf_extraction():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    blank = extract(document(buf.getvalue()), buf.getvalue())
    assert blank["chunks"] == [] and blank["coverage"][0]["indexed"] is False
    real = extract(document(demo_pdf()), demo_pdf())
    assert real["chunks"][0]["page"] == 1 and "SYNTHETIC" in real["chunks"][0]["text"]


def test_checksum_size_and_idempotence(tmp_path):
    data = demo_pdf()
    doc = document(data)
    storage = LocalStorage(tmp_path / "storage")
    storage.store(doc.storage_key, data)
    directory = tmp_path / "index"
    allow = {str(doc.id): doc.checksum_sha256}
    first = build_index([doc], storage, directory, allow, {})
    path = directory / f"{doc.id}.json"
    before, mtime = path.read_bytes(), path.stat().st_mtime_ns
    assert build_index([doc], storage, directory, allow, {}) == first
    assert path.read_bytes() == before and path.stat().st_mtime_ns == mtime
    doc.source_id = uuid4()
    with pytest.raises(ValueError):
        load_index(path, doc)
    storage.store(doc.storage_key, b"changed")
    with pytest.raises(ValueError, match="CHECKSUM"):
        read_pdf(storage, doc)
    assert (
        build_index([doc], storage, directory, allow, {})["documents"][0]["admissible"]
        is False
    )
    with storage.path(doc.storage_key).open("wb") as f:
        f.truncate(MAX_BYTES + 1)
    with pytest.raises(ValueError, match="SIZE"):
        read_pdf(storage, doc)


def test_authorization_and_corrupt_index(tmp_path):
    assert load_allowlist(None) == {}
    path = tmp_path / "allow.json"
    atomic_json(path, {"version": 1, "documents": []})
    assert load_allowlist(path) == {}
    doc = document(demo_pdf())
    index = extract(doc, demo_pdf())
    index["chunks"][0]["text"] = "fabricated"
    atomic_json(path, index)
    with pytest.raises(ValueError):
        load_index(path, doc)
    index = extract(doc, demo_pdf())
    index["chunks"][0]["page"] = 99
    atomic_json(path, index)
    with pytest.raises(ValueError):
        load_index(path, doc)
