"""Opt-in hybrid re-ranking: order may change, evidence and scope never do."""

import pytest
from test_demo_corpus import ask, demo  # noqa: F401 - pytest fixture

from app.core.config import settings
from app.services.rag_lite import hybrid


def row(phrase, score, page, text):
    return (phrase, score, f"doc-{page}", {"page": page, "text": text})


def test_embedding_is_deterministic_normalized_and_accent_folded():
    left = hybrid.embed("Cao trình đỉnh đập")
    assert left == hybrid.embed("Cao trình đỉnh đập")
    assert abs(sum(v * v for v in left.values()) - 1) < 1e-9
    assert hybrid.cosine(left, hybrid.embed("cao trinh dinh dap")) == pytest.approx(1)
    assert hybrid.embed("") == {}


def test_rerank_keeps_exact_phrase_tier_first_and_the_same_rows():
    ranked = [
        row(True, 1.0, 1, "spillway gate pressure"),
        row(False, 2.0, 2, "unrelated words entirely"),
        row(False, 1.0, 3, "crest elevation of the main dam"),
    ]
    result = hybrid.rerank(ranked, "crest elevation main dam")
    assert result[0] is ranked[0]
    assert sorted(id(r) for r in result) == sorted(id(r) for r in ranked)
    assert {r[3]["page"] for r in result[1:]} == {2, 3}


def test_rerank_is_identity_for_fewer_than_two_rows():
    single = [row(True, 1.0, 1, "x")]
    assert hybrid.rerank(single, "x") is single


@pytest.mark.parametrize(
    "question, asset, extra",
    [
        ("homogeneous earthfill", "main_dam", {"query_type": "document"}),
        ("luu luong thiet ke tran xa lu", None, {}),
        ("radial gates", "spillway", {"query_type": "document"}),
        ("filtered prompt-injection probe", None, {}),
        ("current condition of the demo main dam", None, {}),
    ],
)
def test_hybrid_never_changes_evidence_status_or_reasons(
    demo,  # noqa: F811
    monkeypatch,
    question,
    asset,
    extra,
):
    client, _, corpus = demo
    target = getattr(corpus, asset) if asset else None
    monkeypatch.setattr(settings, "rag_hybrid_enabled", False)
    keyword = ask(client, corpus, question, target, **extra)
    monkeypatch.setattr(settings, "rag_hybrid_enabled", True)
    hybrid_result = ask(client, corpus, question, target, **extra)
    assert {c["citation_id"] for c in hybrid_result["citations"]} == {
        c["citation_id"] for c in keyword["citations"]
    }
    assert (hybrid_result["status"], hybrid_result["reason_codes"]) == (
        keyword["status"],
        keyword["reason_codes"],
    )


def test_hybrid_is_off_by_default():
    from app.core.config import Settings

    assert (
        Settings(_env_file=None, database_url="postgresql://unused").rag_hybrid_enabled
        is False
    )
