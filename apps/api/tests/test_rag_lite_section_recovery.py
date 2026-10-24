"""A generic cache rebuild cannot discard a previously reviewed section boundary."""

import pytest
from test_rag_lite_query import rag as rag  # noqa: PLC0414

from app.core.config import settings
from app.services.rag_lite.indexer import build_index, load_allowlist


@pytest.mark.parametrize("missing", [True, False])
def test_scope_pinned_missing_or_incompatible_cache_requires_reviewed_onboarding(
    rag, missing
):
    _, _, _, doc, storage, *_ = rag
    path = settings.rag_lite_index_dir / f"{doc.id}.json"
    if missing:
        path.unlink()
    before = path.read_bytes() if path.exists() else None
    result = build_index(
        [doc],
        storage,
        settings.rag_lite_index_dir,
        load_allowlist(settings.rag_lite_allowlist_path),
        {},
        {str(doc.id): "a" * 64},
    )
    assert result["documents"][0]["status"] == "SECTION_REVIEW_REQUIRED"
    assert not result["documents"][0]["admissible"]
    assert (path.read_bytes() if path.exists() else None) == before
