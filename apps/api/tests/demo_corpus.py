"""SYNTHETIC DEMO DATA — not research evidence.

Test loader for the shared demo corpus in ``app.demo.corpus``. Rows are created
inside the caller's rolled-back test transaction and files only go to a
temporary directory.
"""

from dataclasses import dataclass

from app.demo.corpus import (  # noqa: F401 - re-exported for tests
    DESIGN_DOC_ID,
    DESIGN_PAGES,
    DESIGN_SOURCE_ID,
    LABEL,
    MAIN_DAM_ID,
    NAMESPACE,
    RECORD_SOURCES,
    RESERVOIR_ID,
    SCAN_DOC_ID,
    SPILLWAY_ID,
    SPILLWAY_SOURCE_ID,
    build_pdf,
    demo_id,
    demo_provenance,
    insert_demo_rows,
)
from app.models.asset import Asset
from app.models.asset_technical_attribute import AssetTechnicalAttribute
from app.models.data_source import DataSource
from app.models.media import Document
from app.models.reservoir import Reservoir
from app.services.rag_lite.indexer import atomic_json, build_index
from app.storage.local import LocalStorage


@dataclass
class DemoCorpus:
    reservoir: Reservoir
    main_dam: Asset
    spillway: Asset
    design_source: DataSource
    spillway_source: DataSource
    design_doc: Document
    scan_doc: Document
    records: dict[str, AssetTechnicalAttribute]
    storage: LocalStorage


def load_demo_corpus(db, tmp_path, settings, monkeypatch) -> DemoCorpus:
    """Insert the demo rows into ``db`` (caller rolls back) and index into tmp_path."""
    rows = insert_demo_rows(db)
    storage = LocalStorage(tmp_path / "demo-storage")
    for key, data in rows.files.items():
        storage.store(key, data)

    from app.services import reviewed_provenance

    def provenance(record):
        source_code = RECORD_SOURCES.get(record.id)
        return demo_provenance(source_code) if source_code else None

    monkeypatch.setattr(reviewed_provenance, "technical_provenance", provenance)

    documents = rows.documents
    allowlist = {str(doc.id): doc.checksum_sha256 for doc in documents}
    allow_path = tmp_path / "demo-allowlist.json"
    atomic_json(
        allow_path,
        {
            "version": 1,
            "authorization": "Synthetic demo corpus; no research evidence",
            "documents": [
                {"document_id": key, "checksum_sha256": value}
                for key, value in allowlist.items()
            ],
        },
    )
    monkeypatch.setattr(settings, "rag_lite_enabled", True)
    monkeypatch.setattr(settings, "rag_lite_allowlist_path", allow_path)
    monkeypatch.setattr(settings, "rag_lite_index_dir", tmp_path / "demo-index")
    build_index(documents, storage, settings.rag_lite_index_dir, allowlist, {})
    return DemoCorpus(
        rows.reservoir,
        rows.main_dam,
        rows.spillway,
        rows.design_source,
        rows.spillway_source,
        documents[0],
        documents[1],
        rows.records,
        storage,
    )
