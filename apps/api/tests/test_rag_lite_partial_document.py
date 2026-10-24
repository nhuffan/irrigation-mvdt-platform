"""Synthetic software fixtures for bounded extraction of an unchanged long original."""

import io
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
from test_rag_lite_onboarding import intake as intake  # noqa: PLC0414
from test_rag_lite_query import rag as rag  # noqa: PLC0414

from app.core.config import settings
from app.services.rag_lite.indexer import (
    MAX_BYTES,
    MAX_PAGES,
    atomic_json,
    build_index,
    digest,
    extract,
    inspect_document,
    load_allowlist,
    load_index,
    load_scope_pins,
)
from app.services.rag_lite.onboarding import apply_prepared, outcome, prepare
from app.services.rag_lite.sections import (
    PARTIAL_PROFILE,
    PROFILE,
    extract_sections,
    reviewed_pages,
    scope_digest,
    scoped_chunks,
)
from app.storage.local import LocalStorage
from scripts.seed_media import demo_pdf


@pytest.fixture(scope="module")
def long_original():
    template = PdfReader(io.BytesIO(demo_pdf())).pages[0]
    writer = PdfWriter()
    for number in range(1, 356):
        page = deepcopy(template)
        stream = DecodedStreamObject()
        stream.set_data(
            f"BT /F1 12 Tf 45 740 Td (Intake A Synthetic field on physical page {number}. Never research evidence.) Tj 0 -30 Td (Intake B Synthetic unrelated component, no inherited attribution.) Tj ET".encode()
        )
        page[NameObject("/Contents")] = stream
        writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def section(asset_id, page):
    return {
        "page": page,
        "start": "Intake A",
        "end": "Intake B",
        "asset_ids": [str(asset_id)],
    }


def fixture_index(data, pages=(302, 355)):
    asset_id = str(uuid4())
    doc = SimpleNamespace(
        id=uuid4(),
        source_id=uuid4(),
        checksum_sha256=digest(data),
        page_count=355,
        storage_key="long.pdf",
    )
    index = extract_sections(
        doc,
        data,
        [section(asset_id, p) for p in pages],
        "Synthetic software boundary review",
        list(pages),
    )
    return doc, asset_id, index


def test_selected_extraction_retains_original_count_and_physical_pages(
    tmp_path, long_original, monkeypatch
):
    assert len(long_original) < MAX_BYTES and MAX_PAGES == 300
    from pypdf._page import PageObject

    calls = []
    original_extract = PageObject.extract_text

    def track(page, *args, **kwargs):
        calls.append(page)
        return original_extract(page, *args, **kwargs)

    monkeypatch.setattr(PageObject, "extract_text", track)
    doc, asset_id, index = fixture_index(long_original)
    assert len(calls) == 2
    assert index["page_count"] == 355 and index["included_pages"] == [302, 355]
    assert [p["page"] for p in index["coverage"]] == [302, 355]
    assert [c["page"] for c in scoped_chunks(index, asset_id)] == [302, 355]
    assert all("Intake B" not in c["text"] for c in scoped_chunks(index, asset_id))
    assert all(c["page"] in [302, 355] for c in index["chunks"])
    path = tmp_path / "index.json"
    atomic_json(path, index)
    assert load_index(path, doc) == index
    again = extract_sections(
        doc,
        long_original,
        [section(asset_id, p) for p in [302, 355]],
        "Synthetic software boundary review",
        [355, 302],
    )
    assert again == index
    assert not scoped_chunks(index, str(uuid4()))
    with pytest.raises(ValueError, match="PAGE_COUNT_LIMIT"):
        extract(doc, long_original)
    with pytest.raises(ValueError, match="PAGE_COUNT_LIMIT"):
        extract_sections(
            doc, long_original, [section(asset_id, 302)], "Synthetic review"
        )


@pytest.mark.parametrize(
    "pages",
    [[], [0], [356], [302, 302], [True], [1.0], "302", list(range(1, 302))],
)
def test_invalid_or_over_budget_partial_selection_is_rejected(pages):
    with pytest.raises(ValueError, match="INCLUDED_PAGES"):
        reviewed_pages(355, pages)
    assert len(reviewed_pages(355, list(range(1, 301)))) == 300


def test_partial_selection_requires_review_and_mapped_page(long_original):
    doc, asset_id, _ = fixture_index(long_original)
    with pytest.raises(ValueError, match="REQUIRES_SECTIONS"):
        extract_sections(doc, long_original, [], "Synthetic review", [302])
    with pytest.raises(ValueError, match="REVIEW_REFERENCE"):
        extract_sections(doc, long_original, [section(asset_id, 302)], "", [302])
    with pytest.raises(ValueError, match="SECTION_PAGE_INVALID"):
        extract_sections(
            doc, long_original, [section(asset_id, 355)], "Synthetic review", [302]
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda i: i.update(included_pages=[1, 302, 355]),
        lambda i: i.update(included_pages=[355, 302]),
        lambda i: i.update(page_count=354),
        lambda i: i.update(profile=PROFILE),
        lambda i: i["chunks"].pop(),
        lambda i: i["coverage"].pop(),
        lambda i: i["coverage"][0].update(indexed=False),
        lambda i: i["coverage"][0].update(characters=9999),
        lambda i: i["chunks"][0].update(page=1),
        lambda i: i.pop("profile"),
    ],
)
def test_partial_cache_completeness_and_page_scope_tamper_fail_closed(
    tmp_path, long_original, change
):
    doc, _, index = fixture_index(long_original)
    change(index)
    path = tmp_path / "index.json"
    atomic_json(path, index)
    with pytest.raises((ValueError, KeyError)):
        load_index(path, doc)


def test_partial_runtime_authorization_and_generic_recovery(tmp_path, long_original):
    doc, asset_id, index = fixture_index(long_original)
    storage = LocalStorage(tmp_path / "storage")
    storage.store(doc.storage_key, long_original)
    cfg = SimpleNamespace(
        rag_lite_index_dir=tmp_path / "indexes",
        rag_lite_allowlist_path=tmp_path / "allow.json",
    )
    path = cfg.rag_lite_index_dir / f"{doc.id}.json"
    atomic_json(path, index)
    atomic_json(
        cfg.rag_lite_allowlist_path,
        {
            "version": 1,
            "authorization": "Synthetic permission",
            "documents": [
                {
                    "document_id": str(doc.id),
                    "checksum_sha256": doc.checksum_sha256,
                    "scope_sha256": index["scope_sha256"],
                }
            ],
        },
    )
    allow = load_allowlist(cfg.rag_lite_allowlist_path)
    pins = load_scope_pins(cfg.rag_lite_allowlist_path)
    loaded, issues = inspect_document(storage, cfg, doc, allow)
    assert loaded == index and issues == ["EXTRACTION_LIMITED"]
    assert inspect_document(None, cfg, doc, {}) == (None, ["NOT_AUTHORIZED"])
    entry = build_index([doc], storage, cfg.rag_lite_index_dir, allow, {}, pins)[
        "documents"
    ][0]
    assert entry["page_count"] == 355 and entry["processed_pages"] == 2
    assert entry["omitted_pages"] == 353 and entry["partial"]
    original_bytes = path.read_bytes()
    entry = build_index([doc], storage, cfg.rag_lite_index_dir, allow, {}, {})[
        "documents"
    ][0]
    assert (
        entry["status"] == "SECTION_REVIEW_REQUIRED"
        and path.read_bytes() == original_bytes
    )
    # A self-consistent extra selected page is still outside the admitted scope pin.
    forged = extract_sections(
        doc,
        long_original,
        [section(asset_id, p) for p in [1, 302, 355]],
        "Synthetic software boundary review",
        [1, 302, 355],
    )
    atomic_json(path, forged)
    assert inspect_document(storage, cfg, doc, allow) == (None, ["INDEX_INVALID"])
    path.unlink()
    entry = build_index([doc], storage, cfg.rag_lite_index_dir, allow, {}, pins)[
        "documents"
    ][0]
    assert entry["status"] == "SECTION_REVIEW_REQUIRED" and not path.exists()
    atomic_json(path, index)
    storage.store(doc.storage_key, b"changed original")
    assert inspect_document(storage, cfg, doc, allow) == (None, ["DOCUMENT_INVALID"])


def test_partial_onboarding_is_idempotent_without_changing_original_or_fields(
    intake, long_original
):
    rag_data, db, entry = intake
    storage = rag_data[4]
    Path(entry["file"]).write_bytes(long_original)
    asset_id = entry["asset_ids"][0]
    entry.update(
        checksum_sha256=digest(long_original),
        included_pages=[302, 355],
        sections=[section(asset_id, p) for p in [302, 355]],
    )
    prepared = prepare(db, storage, settings, [entry], "Synthetic permission")
    doc = prepared[0][0]
    report = outcome(prepared, False)["documents"][0]
    assert report["partial"] and report["processed_pages"] == 2
    assert report["page_count"] == 355 and report["omitted_pages"] == 353
    assert report["new_reviewed_fields"] == []
    apply_prepared(db, storage, settings, prepared, "Synthetic permission")
    assert storage.path(doc.storage_key).read_bytes() == long_original
    assert doc.page_count == 355 and doc.checksum_sha256 == digest(long_original)
    again = prepare(db, storage, settings, [entry])
    assert outcome(again, False)["documents"][0]["status"] == "SKIPPED"
    path = settings.rag_lite_index_dir / f"{doc.id}.json"
    before = path.read_bytes()
    apply_prepared(db, storage, settings, again)
    assert path.read_bytes() == before
    assert load_index(path, doc)["profile"] == PARTIAL_PROFILE
    with pytest.raises(ValueError, match="PAGE_COUNT_LIMIT"):
        prepare(db, storage, settings, [{**entry, "included_pages": None}])


def test_full_section_profile_identity_stays_unchanged():
    data = demo_pdf()
    doc = SimpleNamespace(id=uuid4(), source_id=uuid4(), checksum_sha256=digest(data))
    index = extract_sections(doc, data, [], "Synthetic review")
    assert index["profile"] == PROFILE and "included_pages" not in index
    assert index["scope_sha256"] == scope_digest([], "Synthetic review")


def test_cli_included_page_flags_are_explicit_and_preserve_physical_ids(
    tmp_path, monkeypatch
):
    from contextlib import nullcontext

    from scripts import onboard_rag_lite as cli

    asset = str(uuid4())
    seen = []
    monkeypatch.setattr(cli, "SessionLocal", lambda: nullcontext(None))
    monkeypatch.setattr(
        cli,
        "prepare",
        lambda db, storage, cfg, entries, permission: seen.extend(entries) or [],
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "onboard",
            "--file",
            str(tmp_path / "long.pdf"),
            "--source-code",
            "TEST",
            "--document-code",
            "NEW",
            "--asset-id",
            asset,
            "--section",
            f"355|{asset}|Intake A|Intake B",
            "--scope-review",
            "Synthetic review",
            "--include-page",
            "355",
        ],
    )
    assert cli.main() == 0 and seen[0]["included_pages"] == [355]
