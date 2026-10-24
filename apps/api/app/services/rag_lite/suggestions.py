"""Suggestions are returned only when current scoped originals actually match."""

from app.services.rag_lite.indexer import inspect_document, load_allowlist
from app.services.rag_lite.retriever import (
    documents_for_reservoir,
    rank_document_chunks,
    reviewed_records,
    tokens,
)
from app.services.rag_lite.sections import scoped_chunks


def suggested_questions(db, storage, settings, asset):
    records = [
        r
        for r in reviewed_records(db, asset.id)
        if r.source.reservoir_id == asset.reservoir_id
        and (r.value_number is not None or (r.value_text and r.value_text.strip()))
    ]
    fields = [
        {
            "question": r.attribute_label.partition(" theo ")[0],
            "attribute_key": r.attribute_key,
            "attribute_label": r.attribute_label,
        }
        for r in records[:8]
    ]
    source_ids = {r.source_id for r in records}
    candidates = []
    for doc in documents_for_reservoir(db, asset.reservoir_id):
        if doc.source_id not in source_ids:
            continue
        index, _ = inspect_document(
            storage, settings, doc, load_allowlist(settings.rag_lite_allowlist_path)
        )
        if index:
            candidates.extend(
                (doc, c, tokens(c["text"])) for c in scoped_chunks(index, asset.id)
            )
    seen = set()
    # Controlled engineering vocabulary; no asset-specific demo-question overrides.
    for phrase in (
        "vật liệu đập",
        "tường bentonite",
        "thoát nước",
        "quan trắc thấm",
        "cao trình đỉnh",
        "chiều dài đỉnh",
        "cao trình ngưỡng",
        "lưu lượng",
        "cửa chính",
        "bồn nước",
        "sê nô",
    ):
        ranked = rank_document_chunks(
            candidates,
            phrase,
            tokens(phrase) - tokens(asset.name) - tokens(asset.asset_code),
        )
        if not ranked or ranked[0][3]["chunk_id"] in seen:
            continue
        seen.add(ranked[0][3]["chunk_id"])
        fields.append(
            {
                "question": phrase,
                "attribute_key": None,
                "attribute_label": phrase,
                "query_type": "document",
            }
        )
        if len(seen) == 3:
            break
    return fields
