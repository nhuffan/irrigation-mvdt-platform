"""Synthetic ranking regressions; these are not domain-relevance measurements."""

import unicodedata
from types import SimpleNamespace

import pytest

from app.services.rag_lite.retriever import rank_document_chunks, tokens


def rank(question, passages):
    doc = SimpleNamespace(id="synthetic-document")
    candidates = [
        (doc, {"page": page, "offset": 0, "text": text}, tokens(text))
        for page, text in enumerate(passages, 1)
    ]
    return rank_document_chunks(candidates, question, tokens(question))


@pytest.mark.parametrize("question", ["áp suất thử nghiệm", "ap suat thu nghiem"])
def test_all_keywords_exclude_partial_vietnamese_collisions(question):
    passages = [
        "Áp suất thử nghiệm: historical cylinder fixture.",
        "Công suất điện; nguồn thứ cấp ổn áp.",
        "Thử nghiệm thùng dầu; áp tô mát tổng.",
        "Kiểm tra thứ tự pha và áp suất dầu.",
    ]
    results = rank(question, passages)
    assert [row[3]["page"] for row in results] == [1]
    assert results[0][3]["text"] == passages[0]


def test_exact_phrase_outranks_shorter_scattered_keywords():
    passages = [
        "Áp suất và thử tại xưởng; nghiệm là một từ riêng.",
        "ÁP SUẤT: thử-nghiệm " + "longer documentary context " * 30,
    ]
    results = rank("Find áp suất thử nghiệm", passages)
    assert [row[3]["page"] for row in results] == [2, 1]


def test_phrase_keeps_interior_stop_words():
    passages = [
        "test pressure contest",
        "contest pressure test",
        "test of pressure " + "longer documentary context " * 30,
    ]
    # Removing the interior stop word would invent an exact phrase on page 1.
    results = rank("test of pressure", passages)
    assert results[0][3]["page"] == 3
    assert len(results) == 3


def test_phrase_uses_whole_word_boundaries():
    passages = [
        "contest pressure test",
        "test pressure " + "longer documentary context " * 30,
    ]
    # A raw substring match would falsely reward the shorter 'contest' passage.
    assert [row[3]["page"] for row in rank("test pressure", passages)] == [2, 1]


def test_phrase_retains_accent_folding_for_orthographic_variants():
    passages = [
        "thuỷ ở đoạn đầu và lực ở đoạn cuối",
        "Thuỷ lực " + "longer documentary context " * 30,
    ]
    results = rank("thủy lực", passages)
    assert [row[3]["page"] for row in results] == [2, 1]
    assert results[0][3]["text"] == passages[1]


@pytest.mark.parametrize("question", ["what the document", "unknown spaceship"])
def test_no_meaningful_or_matching_keywords_return_no_passages(question):
    assert rank(question, ["Synthetic inspection with historical pressure."]) == []


def test_ties_are_repeatable_and_use_document_page_offset_order():
    doc_b, doc_a = SimpleNamespace(id="b"), SimpleNamespace(id="a")
    text = "historical pressure"
    candidates = [
        (doc_b, {"page": 1, "offset": 0, "text": text}, tokens(text)),
        (doc_a, {"page": 2, "offset": 1400, "text": text}, tokens(text)),
        (doc_a, {"page": 2, "offset": 0, "text": text}, tokens(text)),
        (doc_a, {"page": 1, "offset": 0, "text": text}, tokens(text)),
    ]
    first = rank_document_chunks(candidates, "pressure", {"pressure"})
    second = rank_document_chunks(list(reversed(candidates)), "pressure", {"pressure"})
    assert first == second
    assert [(row[2].id, row[3]["page"], row[3]["offset"]) for row in first] == [
        ("a", 1, 0),
        ("a", 2, 0),
        ("a", 2, 1400),
        ("b", 1, 0),
    ]


@pytest.mark.parametrize(
    "question, matching, collision",
    [
        (
            "chiều dày tường tâm",
            "Chiều dày tường tâm: 0.6 m.",
            "Chiều dài tường, cao trình đáy, tràn tam giác.",
        ),
        ("dày", "dày", "đáy"),
        ("dày", "dày", "đây"),
        ("thử", "thử", "thứ"),
        ("áp", "áp", "ấp"),
        ("bàn", "bàn", "bán"),
        ("café", "café", "cafe"),
        ("đập", "đập", "dập"),
    ],
)
def test_explicit_diacritics_exclude_distinct_folded_words(
    question, matching, collision
):
    assert [row[3]["page"] for row in rank(question, [matching, collision])] == [1]


@pytest.mark.parametrize(
    "question, passages",
    [
        ("day", ["dày", "đáy", "đây"]),
        ("thu", ["thử", "thứ"]),
        ("ap", ["áp", "ấp"]),
        ("ban", ["bàn", "bán"]),
        ("cafe", ["café", "cafe"]),
        ("dap", ["đập", "dập"]),
    ],
)
def test_unaccented_queries_retain_accent_insensitive_matches(question, passages):
    assert [row[3]["page"] for row in rank(question, passages)] == list(
        range(1, len(passages) + 1)
    )


@pytest.mark.parametrize(
    "question, passage",
    [
        ("THỦY LỰC", "Thuỷ lực"),
        ("thuỷ lực", "thủy lực"),
        (unicodedata.normalize("NFD", "thủy lực"), "thuỷ lực"),
        ("thủy lực", unicodedata.normalize("NFD", "thuỷ lực")),
    ],
)
def test_diacritics_preserve_unicode_and_tone_position_variants(question, passage):
    assert [row[3]["page"] for row in rank(question, [passage])] == [1]


def test_mixed_query_only_constrains_explicit_meaningful_diacritics():
    passages = [
        "Chiều dày tường tâm.",
        "Chiều dài tường, cao trình đáy, tràn tam giác.",
    ]
    assert [row[3]["page"] for row in rank("chieu dày tuong tam", passages)] == [1]
    assert len(rank("Find thông số thủy lực", ["Thuỷ lực"])) == 1
