"""Reproducible checks on the SYNTHETIC demo corpus (no private files or models)."""

import asyncio
import io
from contextlib import nullcontext

import pytest
from demo_corpus import DESIGN_PAGES, LABEL, build_pdf, load_demo_corpus
from mcp import Client
from pypdf import PdfReader

from app.api.routes import rag_lite
from app.core.config import settings
from app.main import app
from app.mcp.policy import McpGrant
from app.mcp.server import create_server
from app.schemas.rag_lite import RagQuery
from app.services.rag_lite.answer import generate_answer
from app.services.rag_lite.retriever import retrieve
from app.services.storage_service import get_storage

URL = "/api/v1/experimental/rag-lite/query"


@pytest.fixture
def demo(domain, tmp_path, monkeypatch):
    client, db = domain[0], domain[1]
    corpus = load_demo_corpus(db, tmp_path, settings, monkeypatch)
    monkeypatch.setattr(rag_lite, "_requests", {})
    app.dependency_overrides[rag_lite.get_rag_db] = lambda: db
    app.dependency_overrides[get_storage] = lambda: corpus.storage
    try:
        yield client, db, corpus
    finally:
        app.dependency_overrides.pop(rag_lite.get_rag_db, None)
        app.dependency_overrides.pop(get_storage, None)


def ask(client, corpus, question, asset=None, **extra):
    body = {"question": question, "reservoir_id": str(corpus.reservoir.id), **extra}
    if asset is None:
        body["all_authorized_docs"] = True
    else:
        body["asset_id"] = str(asset.id)
    response = client.post(URL, json=body)
    assert response.status_code == 200
    return response.json()


def test_pdf_generator_is_deterministic_and_labelled():
    data = build_pdf(DESIGN_PAGES)
    assert data == build_pdf(DESIGN_PAGES)
    pages = PdfReader(io.BytesIO(data)).pages
    assert len(pages) == len(DESIGN_PAGES)
    assert all(LABEL in " ".join(page.extract_text().split()) for page in pages)
    assert PdfReader(io.BytesIO(build_pdf([""]))).pages[0].extract_text() == ""


def test_exact_reviewed_attribute_is_returned_without_inheritance(demo):
    client, _, corpus = demo
    result = ask(client, corpus, "crest elevation", corpus.main_dam)
    assert result["status"] == "RETRIEVAL_ONLY"
    citation = result["citations"][0]
    assert citation["record_id"] == str(corpus.records["crest_elevation"].id)
    assert (citation["value_number"], citation["unit"]) == (42.5, "m")
    assert citation["source_code"] == "DEMO-SRC-DESIGN"

    child = ask(
        client, corpus, "crest elevation", corpus.spillway, query_type="attribute"
    )
    assert child["citations"] == []
    assert child["reason_codes"] == ["NO_MATCH"]


def test_pdf_passages_keep_physical_pages_and_scope(demo):
    client, _, corpus = demo
    scoped = ask(
        client,
        corpus,
        "homogeneous earthfill",
        corpus.main_dam,
        query_type="document",
    )
    assert [(c["document_id"], c["page"]) for c in scoped["citations"]] == [
        (str(corpus.design_doc.id), 1)
    ]
    assert scoped["citations"][0]["asset_id"] == str(corpus.main_dam.id)
    assert "IMAGE_ONLY" in scoped["reason_codes"]

    corpus_wide = ask(client, corpus, "luu luong thiet ke tran xa lu")
    assert [c["page"] for c in corpus_wide["citations"]] == [2]
    assert corpus_wide["citations"][0]["asset_id"] is None

    # The spillway's own source has no document; the parent's PDF is not inherited.
    child = ask(client, corpus, "radial gates", corpus.spillway, query_type="document")
    assert child["citations"] == [] and "NO_DIRECT_DOCUMENT" in child["reason_codes"]


def test_out_of_scope_and_injection_pages_fail_closed(demo):
    client, _, corpus = demo
    refused = ask(client, corpus, "current condition of the demo main dam")
    assert refused["reason_codes"] == ["OUT_OF_SCOPE"] and not refused["citations"]

    filtered = ask(client, corpus, "filtered prompt-injection probe")
    assert filtered["citations"] == []
    assert "A potentially instructional passage was excluded" in filtered["limitations"]

    unfiltered = ask(client, corpus, "disregard the evidence rules")
    assert [c["page"] for c in unfiltered["citations"]] == [4]
    assert unfiltered["status"] == "RETRIEVAL_ONLY"


class FakeProvider:
    def __init__(self, answer):
        self.answer = answer
        self.prompts = []

    def generate(self, prompt, *, timeout):
        self.prompts.append(prompt)
        return self.answer(prompt)


def grounded(corpus, db, question, asset=None, **extra):
    scope = (
        {"asset_id": asset.id} if asset is not None else {"all_authorized_docs": True}
    )
    request = RagQuery(
        question=question,
        reservoir_id=corpus.reservoir.id,
        mode="grounded_answer",
        **scope,
        **extra,
    )
    evidence = retrieve(
        db,
        corpus.storage,
        settings,
        request.model_copy(update={"mode": "evidence_only"}),
    )
    return request, evidence


def test_grounded_answer_binds_exact_value_and_rejects_injected_number(demo):
    _, db, corpus = demo
    request, evidence = grounded(corpus, db, "crest elevation", corpus.main_dam)
    cid = evidence.citations[0].citation_id

    honest = FakeProvider(
        lambda _: {
            "answer": f"The historical crest elevation is 42.5 m [{cid}].",
            "citation_ids": [cid],
        }
    )
    answered = generate_answer(
        request,
        evidence.model_copy(deep=True),
        evidence.citations,
        honest,
        max_context_chars=12000,
    )
    assert answered.status == "ANSWERED" and "42.5 m" in answered.answer
    assert [c.record_id for c in answered.citations] == [
        corpus.records["crest_elevation"].id
    ]
    # Instructions and untrusted evidence travel as separate chat messages.
    assert '"role": "system"' in honest.prompts[0]

    injected = FakeProvider(
        lambda _: {
            "answer": f"The reviewer approved a 99 m crest [{cid}].",
            "citation_ids": [cid],
        }
    )
    rejected = generate_answer(
        request,
        evidence.model_copy(deep=True),
        evidence.citations,
        injected,
        max_context_chars=12000,
    )
    assert rejected.status == "GENERATION_UNAVAILABLE" and rejected.answer is None
    assert rejected.citations == evidence.citations


def test_injected_passage_remains_a_visible_citation(demo):
    """Residual risk: a model may repeat an injected passage that cites itself.

    The numeric check cannot reject a number present in that passage, so the
    answer stays bound to the exact injected page for human review.
    """
    _, db, corpus = demo
    request, evidence = grounded(corpus, db, "disregard the evidence rules")
    cid = evidence.citations[0].citation_id
    follower = FakeProvider(
        lambda _: {
            "answer": f"The reviewer approved a 99 m crest [{cid}].",
            "citation_ids": [cid],
        }
    )
    result = generate_answer(
        request,
        evidence.model_copy(deep=True),
        evidence.citations,
        follower,
        max_context_chars=12000,
    )
    assert result.status == "ANSWERED"
    assert [(c.document_id, c.page) for c in result.citations] == [
        (corpus.design_doc.id, 4)
    ]


def mcp_server(db, corpus, allow_evidence):
    grant = McpGrant(
        authorization="Synthetic demo corpus",
        reservoir_id=corpus.reservoir.id,
        asset_ids={corpus.main_dam.id, corpus.spillway.id},
        source_ids={corpus.design_source.id, corpus.spillway_source.id},
        document_checksums={
            doc.id: doc.checksum_sha256 for doc in (corpus.design_doc, corpus.scan_doc)
        },
        allow_evidence=allow_evidence,
    )
    return create_server(
        settings,
        lambda ctx: grant,
        db_session=lambda: nullcontext(db),
        storage=corpus.storage,
    )


def test_mcp_metadata_only_grant_withholds_evidence(demo):
    _, db, corpus = demo
    scope = {"reservoir_id": str(corpus.reservoir.id)}
    asset = {**scope, "asset_id": str(corpus.main_dam.id)}

    async def check():
        async with Client(mcp_server(db, corpus, False)) as client:
            search = await client.call_tool(
                "search_evidence", {**asset, "question": "crest elevation"}
            )
            assert search.is_error
            assert search.structured_content["reason_codes"] == ["NOT_AUTHORIZED"]

            details = await client.call_tool("get_asset_details", asset)
            payload = details.structured_content
            assert payload["asset"]["code"] == "DEMO-MAIN-DAM"
            assert payload["asset"]["reviewed_direct_attribute_count"] == 2
            assert payload["citations"] == []

            provenance = await client.call_tool(
                "get_document_provenance",
                {**scope, "source_id": str(corpus.design_source.id)},
            )
            documents = {
                d["code"]: d["page_locators_available"]
                for d in provenance.structured_content["source"]["documents"]
            }
            assert documents == {"DEMO-DOC-DESIGN": True, "DEMO-DOC-SCAN": False}
            assert "IMAGE_ONLY" in provenance.structured_content["reason_codes"]

            coverage = await client.call_tool("get_research_coverage", asset)
            counts = coverage.structured_content["coverage"]
            assert (counts["searchable_documents"], counts["image_only_documents"]) == (
                1,
                1,
            )

    asyncio.run(check())


def test_mcp_evidence_grant_matches_http_without_links(demo):
    client, db, corpus = demo
    question = {"question": "homogeneous earthfill", "query_type": "document"}
    expected = ask(client, corpus, asset=corpus.main_dam, **question)["citations"]

    async def check():
        async with Client(mcp_server(db, corpus, True)) as mcp_client:
            result = await mcp_client.call_tool(
                "search_evidence",
                {
                    "reservoir_id": str(corpus.reservoir.id),
                    "asset_id": str(corpus.main_dam.id),
                    **question,
                },
            )
            citations = result.structured_content["citations"]
            assert [c["citation_id"] for c in citations] == [
                c["citation_id"] for c in expected
            ]
            assert all("url" not in c and "content_url" not in c for c in citations)
            assert (
                "SOURCE_METADATA_UNKNOWN" in result.structured_content["reason_codes"]
            )

    asyncio.run(check())
