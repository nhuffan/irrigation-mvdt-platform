"""Synthetic software fixtures only. Never imports fabricated research evidence."""

import io
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
from sqlalchemy import func, select
from test_rag_lite_query import URL
from test_rag_lite_query import rag as rag  # noqa: PLC0414

from app.core.config import settings
from app.models.media import Document
from app.services.rag_lite.indexer import (
    atomic_json,
    digest,
    inspect_document,
    load_allowlist,
    load_index,
)
from app.services.rag_lite.onboarding import apply_prepared, outcome, prepare
from app.services.rag_lite.retriever import (
    attribute_matches,
    rank_document_chunks,
    tokens,
)
from app.services.rag_lite.sections import extract_sections, scoped_chunks
from app.storage.local import LocalStorage


@pytest.fixture
def intake(rag, domain, tmp_path):
    _, body, _, doc, storage, _, _ = rag
    writer = PdfWriter()
    reader = PdfReader(io.BytesIO(storage.path(doc.storage_key).read_bytes()))
    for _ in range(11):
        page = deepcopy(reader.pages[0])
        stream = DecodedStreamObject()
        stream.set_data(
            b"BT /F1 12 Tf 45 740 Td (Section A Crest Elevation +28.0 m. Earthfilll construction. Synthetic evidence only.) Tj 0 -30 Td (Section B Other component test pressure 270 bar. No asset inheritance.) Tj ET"
        )
        page[NameObject("/Contents")] = stream
        writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)
    path = tmp_path / "additional.pdf"
    path.write_bytes(output.getvalue())
    entry = {
        "file": str(path),
        "source_code": doc.source.source_code,
        "document_code": f"T-NEW-{uuid4()}",
        "checksum_sha256": digest(output.getvalue()),
        "asset_ids": [body["asset_id"]],
        "scope_review": "Synthetic boundary review, no domain attestation",
        "sections": [
            {
                "page": n,
                "start": "Section A",
                "end": "Section B",
                "asset_ids": [body["asset_id"]],
            }
            for n in range(1, 12)
        ],
    }
    return rag, domain[1], entry


def test_dry_run_no_writes_then_apply_deduplicate_and_preserve_unrelated(intake):
    rag_data, db, entry = intake
    _, body, _, original, storage, _, _ = rag_data
    count = db.scalar(select(func.count()).select_from(Document))
    paths = [
        settings.rag_lite_allowlist_path,
        settings.rag_lite_index_dir / f"{original.id}.json",
    ]
    before = {p: p.read_bytes() for p in paths}
    with pytest.raises(ValueError, match="AUTHORIZATION_REQUIRED"):
        prepare(db, storage, settings, [entry])
    prepared = prepare(db, storage, settings, [entry], "Explicit synthetic permission")
    assert db.scalar(select(func.count()).select_from(Document)) == count
    assert all(p.read_bytes() == data for p, data in before.items())
    assert not storage.path(prepared[0][0].storage_key).exists()
    assert outcome(prepared, False)["documents"][0]["status"] == "WOULD_IMPORT"
    apply_prepared(db, storage, settings, prepared, "Explicit synthetic permission")
    document = prepared[0][0]
    assert db.scalar(select(func.count()).select_from(Document)) == count + 1
    assert document.source.verification_status == "UNVERIFIED"
    assert (settings.rag_lite_index_dir / f"{original.id}.json").read_bytes() == before[
        paths[1]
    ]
    index, issues = inspect_document(
        storage, settings, document, load_allowlist(settings.rag_lite_allowlist_path)
    )
    assert not issues and len(scoped_chunks(index, body["asset_id"])) == 11
    pin_before = settings.rag_lite_allowlist_path.read_bytes()
    again = prepare(db, storage, settings, [entry])
    assert outcome(again, True)["documents"][0]["status"] == "SKIPPED"
    apply_prepared(db, storage, settings, again)
    assert settings.rag_lite_allowlist_path.read_bytes() == pin_before
    assert db.scalar(select(func.count()).select_from(Document)) == count + 1


def test_scoped_pages_pagination_and_cross_component_isolation(intake):
    rag_data, db, entry = intake
    client, body, assets, _, storage, *_ = rag_data
    prepared = prepare(db, storage, settings, [entry], "Synthetic permission")
    apply_prepared(db, storage, settings, prepared, "Synthetic permission")
    doc = prepared[0][0]
    query = {
        **body,
        "query_type": "document",
        "question": "vật liệu đập",
        "page_size": 5,
    }
    pages = []
    ids = []
    for page in [1, 2, 3]:
        result = client.post(URL, json={**query, "page": page}).json()
        assert result["pagination"]["total_results"] == 11
        for c in result["citations"]:
            assert c["document_id"] == str(doc.id) and c["asset_id"] == body["asset_id"]
            assert "Section B" not in c["excerpt"]
            original = " ".join(
                (
                    PdfReader(storage.path(doc.storage_key))
                    .pages[c["page"] - 1]
                    .extract_text()
                    or ""
                ).split()
            )
            assert c["excerpt"] in original
        pages += [c["page"] for c in result["citations"]]
        ids += [c["citation_id"] for c in result["citations"]]
    assert pages == list(range(1, 12)) and len(set(ids)) == 11
    assert (
        client.post(
            URL, json={**query, "page": 1, "asset_id": str(assets[1].id)}
        ).json()["citations"]
        == []
    )
    assert not client.post(
        URL, json={**query, "page": 1, "question": "270 bar"}
    ).json()["citations"]
    corpus = client.post(
        URL,
        json={
            **query,
            "page": 1,
            "question": "270 bar",
            "asset_id": None,
            "all_authorized_docs": True,
        },
    ).json()
    assert corpus["citations"] and all(
        c["asset_id"] is None for c in corpus["citations"]
    )
    settings.rag_lite_allowlist_path.write_text(
        '{"version":1,"authorization":"revoked","documents":[]}'
    )
    assert not client.post(URL, json={**query, "page": 2}).json()["citations"]


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"checksum_sha256": "a" * 64}, "CHECKSUM"),
        ({"asset_ids": [str(uuid4())]}, "SOURCE_ASSET_LINK"),
        ({"source_code": "absent"}, "SOURCE_REQUIRED"),
        (
            {"sections": [{"page": 1, "start": "absent", "asset_ids": []}]},
            "START_NOT_UNIQUE",
        ),
        ({"scope_review": ""}, "REVIEW_REFERENCE"),
    ],
)
def test_onboarding_rejects_changed_bytes_wrong_scope_and_unreviewed_boundaries(
    intake, change, reason
):
    rag_data, db, entry = intake
    with pytest.raises(ValueError, match=reason):
        prepare(
            db, rag_data[4], settings, [{**entry, **change}], "Synthetic permission"
        )


def test_scope_pin_and_cached_scope_tamper_fail_closed(intake):
    rag_data, db, entry = intake
    storage = rag_data[4]
    prepared = prepare(db, storage, settings, [entry], "Synthetic permission")
    apply_prepared(db, storage, settings, prepared, "Synthetic permission")
    doc = prepared[0][0]
    path = settings.rag_lite_index_dir / f"{doc.id}.json"
    index = load_index(path, doc)
    index["chunks"][0]["asset_ids"] = []
    atomic_json(path, index)
    assert inspect_document(
        storage, settings, doc, load_allowlist(settings.rag_lite_allowlist_path)
    )[1] == ["INDEX_INVALID"]
    index = prepared[0][3]
    atomic_json(path, index)
    allow = json.loads(settings.rag_lite_allowlist_path.read_text())
    allow["documents"][-1].pop("scope_sha256")
    atomic_json(settings.rag_lite_allowlist_path, allow)
    assert inspect_document(
        storage, settings, doc, load_allowlist(settings.rag_lite_allowlist_path)
    )[1] == ["INDEX_INVALID"]


def test_failed_commit_restores_all_cache_and_permission_bytes(intake, monkeypatch):
    rag_data, db, entry = intake
    storage = rag_data[4]
    prepared = prepare(db, storage, settings, [entry], "Synthetic permission")
    original = rag_data[3]
    original_bytes = storage.path(original.storage_key).read_bytes()
    created_path = storage.path(prepared[0][0].storage_key)
    assert not created_path.exists()
    before = {
        p: p.read_bytes()
        for p in [
            settings.rag_lite_allowlist_path,
            settings.rag_lite_index_dir / "rag_corpus_manifest.json",
        ]
    }
    monkeypatch.setattr(
        db, "commit", lambda: (_ for _ in ()).throw(ValueError("simulated failure"))
    )
    with pytest.raises(ValueError, match="simulated failure"):
        apply_prepared(db, storage, settings, prepared, "Synthetic permission")
    assert all(p.read_bytes() == b for p, b in before.items())
    assert not (settings.rag_lite_index_dir / f"{prepared[0][0].id}.json").exists()
    assert not created_path.exists()
    assert storage.path(original.storage_key).read_bytes() == original_bytes


def test_section_markers_are_unique_and_image_only_remains_empty(intake):
    rag_data, _, entry = intake
    doc = rag_data[3]
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    stream = io.BytesIO()
    writer.write(stream)
    index = extract_sections(doc, stream.getvalue(), [], "Synthetic blank original")
    assert not index["chunks"] and all(c["characters"] == 0 for c in index["coverage"])
    with pytest.raises(ValueError, match="OVERLAPPING_SECTIONS"):
        extract_sections(
            doc,
            Path(entry["file"]).read_bytes(),
            entry["sections"] + [entry["sections"][0]],
            entry["scope_review"],
        )


@pytest.mark.parametrize(
    "question,expected",
    [
        ("ép 0,6 m", True),
        ("ép 0.60m", True),
        ("ép 6 m", False),
        ("ép 0 m", False),
        ("ép 0,6 mm", False),
    ],
)
def test_decimal_comma_and_units_cannot_match_numeric_fragments(question, expected):
    record = SimpleNamespace(
        attribute_key="ep",
        attribute_label="ép",
        value_number=0.6,
        value_text=None,
        unit="m",
    )
    assert attribute_matches(record, question, tokens(question)) is expected


def test_pdf_numeric_literals_do_not_match_fragments_or_change_locale():
    doc = SimpleNamespace(id=uuid4())
    chunk = {
        "chunk_id": "a",
        "page": 1,
        "offset": 0,
        "text": "Synthetic Crest Elevation +28.0 m; length 1,100 m. Groundwater depth 0.6 m.",
    }
    candidates = [(doc, chunk, tokens(chunk["text"]))]
    assert not rank_document_chunks(candidates, "depth 6 m", tokens("depth 6 m"))
    assert rank_document_chunks(candidates, "depth 0,6 m", tokens("depth 0,6 m"))
    assert not rank_document_chunks(
        candidates, "length 1100 m", tokens("length 1100 m")
    )
    assert rank_document_chunks(candidates, "length 1,100 m", tokens("length 1,100 m"))


def test_aliases_preserve_explicit_diacritics_outside_the_concept():
    doc = SimpleNamespace(id=uuid4())
    chunk = {
        "chunk_id": "a",
        "page": 1,
        "offset": 0,
        "text": "Synthetic bentonite core wall chiều đáy 5 m.",
    }
    candidates = [(doc, chunk, tokens(chunk["text"]))]
    assert not rank_document_chunks(
        candidates, "tường bentonite chiều dày", tokens("tường bentonite chiều dày")
    )
    assert rank_document_chunks(
        candidates, "tường bentonite chiều đáy", tokens("tường bentonite chiều đáy")
    )


def test_controlled_material_concept_is_not_generic_material_keyword_overlap():
    doc = SimpleNamespace(id=uuid4())
    chunks = [
        {
            "chunk_id": "a",
            "page": 1,
            "offset": 0,
            "text": "Các vật liệu trong bản vẽ hố quan trắc.",
        },
        {
            "chunk_id": "b",
            "page": 2,
            "offset": 0,
            "text": "Main Dam (Earthfilll) Crest Width 8.0 m.",
        },
    ]
    ranked = rank_document_chunks(
        [(doc, c, tokens(c["text"])) for c in chunks],
        "vật liệu đập",
        tokens("vật liệu"),
    )
    assert [r[3]["chunk_id"] for r in ranked] == ["b"]


def test_operator_selective_manifest_dry_run_without_raw_database_edits(
    tmp_path, monkeypatch
):
    from contextlib import nullcontext

    from scripts import onboard_rag_lite as cli

    manifest = tmp_path / "selection.json"
    manifest.write_text(
        json.dumps({"documents": [{"document_code": "A"}, {"document_code": "B"}]})
    )
    seen = []
    monkeypatch.setattr(cli, "SessionLocal", lambda: nullcontext(None))
    monkeypatch.setattr(
        cli,
        "prepare",
        lambda db, storage, cfg, entries, permission: seen.extend(entries) or [],
    )
    monkeypatch.setattr(
        "sys.argv", ["onboard", "--manifest", str(manifest), "--document-code", "B"]
    )
    assert cli.main() == 0 and seen == [{"document_code": "B"}]


def test_operator_reviewed_section_flags_require_no_json_editing(tmp_path, monkeypatch):
    from contextlib import nullcontext

    from scripts import onboard_rag_lite as cli

    seen = []
    asset = str(uuid4())
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
            str(tmp_path / "original.pdf"),
            "--source-code",
            "TEST",
            "--document-code",
            "NEW",
            "--asset-id",
            asset,
            "--section",
            f"2|{asset}|Main section|Next section",
            "--scope-review",
            "Synthetic section review",
        ],
    )
    assert cli.main() == 0
    assert seen[0]["sections"] == [
        {
            "page": 2,
            "asset_ids": [asset],
            "start": "Main section",
            "end": "Next section",
        }
    ]


@pytest.mark.parametrize("failure_point", ["flush", "commit"])
@pytest.mark.parametrize("preserve", [None, "preexisting", "referenced", "changed"])
def test_apply_failure_cleans_only_new_unreferenced_originals(
    tmp_path, failure_point, preserve
):
    storage = LocalStorage(tmp_path / "originals")
    cfg = SimpleNamespace(
        rag_lite_allowlist_path=tmp_path / "allowlist.json",
        rag_lite_index_dir=tmp_path / "indexes",
    )
    permission = {
        "version": 1,
        "authorization": "Synthetic permission",
        "documents": [],
    }
    atomic_json(cfg.rag_lite_allowlist_path, permission)
    allow_before = cfg.rag_lite_allowlist_path.read_bytes()
    data = b"Synthetic prepared original; no research evidence."
    checksum = digest(data)
    doc = SimpleNamespace(
        id=uuid4(),
        source_id=uuid4(),
        storage_key=f"documents/{checksum}",
        checksum_sha256=checksum,
    )
    path = storage.path(doc.storage_key)
    if preserve == "preexisting":
        storage.store(doc.storage_key, data)
    index = {
        "chunks": [],
        "page_count": 1,
        "coverage": [{"indexed": False, "characters": 0}],
    }
    rolled_back = []

    def fail():
        if preserve == "changed":
            path.write_bytes(b"Different content written by another operation")
        raise ValueError("simulated failure")

    db = SimpleNamespace(
        add=lambda _: None,
        flush=fail if failure_point == "flush" else lambda: None,
        commit=fail if failure_point == "commit" else lambda: None,
        rollback=lambda: rolled_back.append(True),
        scalar=lambda _: uuid4() if preserve == "referenced" else None,
    )
    with pytest.raises(ValueError, match="simulated failure"):
        apply_prepared(
            db,
            storage,
            cfg,
            [(doc, True, data, index, False, set())],
            "Synthetic permission",
        )
    assert rolled_back == [True]
    assert cfg.rag_lite_allowlist_path.read_bytes() == allow_before
    assert not (cfg.rag_lite_index_dir / f"{doc.id}.json").exists()
    assert not (cfg.rag_lite_index_dir / "rag_corpus_manifest.json").exists()
    if preserve:
        assert path.read_bytes() == (
            b"Different content written by another operation"
            if preserve == "changed"
            else data
        )
    else:
        assert not path.exists()


def test_section_file_cannot_replace_the_explicitly_selected_original(
    tmp_path, monkeypatch
):
    from scripts import onboard_rag_lite as cli

    section_file = tmp_path / "untrusted-sections.json"
    section_file.write_text(
        json.dumps({"file": "/different/original.pdf", "sections": []})
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "onboard",
            "--file",
            str(tmp_path / "selected.pdf"),
            "--source-code",
            "TEST",
            "--document-code",
            "NEW",
            "--asset-id",
            str(uuid4()),
            "--sections",
            str(section_file),
        ],
    )
    monkeypatch.setattr(
        cli,
        "prepare",
        lambda *args: pytest.fail("Must reject the override before loading a source"),
    )
    assert cli.main() == 1
