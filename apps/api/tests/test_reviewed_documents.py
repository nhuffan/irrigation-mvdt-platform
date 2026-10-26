import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.data_source import DataSource
from app.models.media import Document
from app.storage.local import LocalStorage
from scripts.import_reviewed_documents import import_reviewed, validate_manifest
from scripts.seed_media import demo_pdf


@pytest.fixture
def package(tmp_path):
    path = tmp_path / "source.pdf"
    path.write_bytes(demo_pdf())
    row = {
        "document_code": "RS-DOC-TEST",
        "source_code": "RS-SRC-TEST",
        "evidence_id": "E-1",
        "drive_file_id": "drive-1",
        "file_name": path.name,
        "mime_type": "application/pdf",
        "file_size": str(path.stat().st_size),
        "checksum_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "page_count": "1",
        "representation_group": "revision-1",
        "document_status": "IMPORT",
        "reviewer": "Synthetic reviewer",
        "reviewed_at": datetime.now(UTC).isoformat(),
        "file_path": path.name,
    }
    evidence = {**row, "review_status": "REVIEWED"}
    return row, evidence, tmp_path


@pytest.mark.parametrize(
    "field,value",
    [
        ("checksum_sha256", "0" * 64),
        ("page_count", "2"),
        ("file_size", "0"),
        ("file_path", "../missing.pdf"),
        ("source_code", "RS-OTHER"),
        ("reviewed_at", "2026-10-09"),
        ("mime_type", "image/png"),
        ("document_status", "VERIFIED"),
    ],
)
def test_review_gate_rejects_mismatch(package, field, value):
    row, evidence, root = package
    row[field] = value
    with pytest.raises((ValueError, KeyError)):
        validate_manifest([row], [evidence], root)


def test_same_physical_file_not_duplicated(package):
    row, evidence, root = package
    with pytest.raises(ValueError, match="Duplicate physical"):
        validate_manifest(
            [row, {**row, "document_code": "RS-DOC-OTHER"}], [evidence], root
        )


def test_reference_excluded(package):
    row, evidence, root = package
    with pytest.raises(ValueError, match="No reviewed"):
        validate_manifest(
            [{**row, "document_status": "REFERENCE_ONLY"}], [evidence], root
        )


def test_document_import_idempotency_and_no_alias(domain, package):
    _, db, reservoir, *_ = domain
    row, evidence, root = package
    row["source_code"] = evidence["source_code"] = "RS-" + str(uuid4())
    source = DataSource(
        reservoir_id=reservoir.id,
        source_code=row["source_code"],
        source_type="OTHER",
        title="Synthetic",
    )
    db.add(source)
    db.flush()
    selected = validate_manifest([row], [evidence], root)
    storage = LocalStorage(root / "storage")
    first = import_reviewed(db, storage, selected)
    second = import_reviewed(db, storage, selected)
    assert first[0]["status"] == "STAGED" and second[0]["status"] == "UNCHANGED"
    assert first[0]["document_id"] == second[0]["document_id"]
    record = db.scalar(select(Document).where(Document.source_id == source.id))
    assert (
        record.page_count == 1
        and storage.path(record.storage_key).read_bytes()
        == (root / "source.pdf").read_bytes()
    )
    row["document_code"] = "RS-DOC-ALIAS"
    with pytest.raises(ValueError, match="identity differs"):
        import_reviewed(db, storage, [(row, root / "source.pdf", 1)])


@pytest.mark.parametrize(
    "pins",
    [
        {"source_id": str(uuid4())},
        {"reservoir_id": str(uuid4())},
        {"source_id": "invalid", "reservoir_id": str(uuid4())},
    ],
)
def test_exact_source_pins_require_both_valid_uuids(package, pins):
    row, evidence, root = package
    row.update(pins)
    evidence.update(pins)
    with pytest.raises(ValueError, match="source_id|UUID"):
        validate_manifest([row], [evidence], root)


def test_manifest_evidence_exact_source_pins_must_agree(package):
    row, evidence, root = package
    row.update(source_id=str(uuid4()), reservoir_id=str(uuid4()))
    evidence.update(source_id=str(uuid4()), reservoir_id=row["reservoir_id"])
    with pytest.raises(ValueError, match="pin mismatch"):
        validate_manifest([row], [evidence], root)


def test_exact_source_original_registration_keeps_source_and_old_documents(
    domain, package
):
    _, db, reservoir, *_ = domain
    row, evidence, root = package
    code = "RS-" + str(uuid4())
    source = DataSource(
        reservoir_id=reservoir.id,
        source_code=code,
        source_type="GIS",
        title="Synthetic GeoPDF source",
        verification_status="UNVERIFIED",
        authority_level="UNKNOWN",
    )
    db.add(source)
    db.flush()
    source_before = {
        column.name: getattr(source, column.name) for column in source.__table__.columns
    }
    old_document_ids = set(db.scalars(select(Document.id)))
    pins = {"source_id": str(source.id), "reservoir_id": str(reservoir.id)}
    row.update(pins, source_code=code)
    evidence.update(pins, source_code=code)
    selected = validate_manifest([row], [evidence], root)
    storage = LocalStorage(root / "storage")
    first = import_reviewed(db, storage, selected)
    second = import_reviewed(db, storage, selected)
    assert first[0]["status"] == "STAGED" and second[0]["status"] == "UNCHANGED"
    assert first[0]["document_id"] == second[0]["document_id"]
    db.refresh(source)
    assert source_before == {
        column.name: getattr(source, column.name) for column in source.__table__.columns
    }
    assert old_document_ids <= set(db.scalars(select(Document.id)))
    document = db.scalar(select(Document).where(Document.source_id == source.id))
    assert document.checksum_sha256 == row["checksum_sha256"]
    assert document.page_count == 1
    assert (
        storage.path(document.storage_key).read_bytes()
        == (root / "source.pdf").read_bytes()
    )
    for wrong in [
        {"source_id": str(uuid4())},
        {"reservoir_id": str(uuid4())},
    ]:
        mismatch = dict(row) | wrong
        with pytest.raises(ValueError, match="Exact source/reservoir identity"):
            import_reviewed(db, storage, [(mismatch, root / "source.pdf", 1)])
