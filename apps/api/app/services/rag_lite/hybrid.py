"""Opt-in hybrid re-ranking for already-admitted PDF passages.

The keyword ranker decides *which* passages are evidence (every meaningful
keyword, numeric literal, diacritic and concept constraint must hold, after
authorization, checksum and section-scope filters). This module only changes
the *order* of that set; it never adds, removes or rescopes a passage.

Similarity uses local, deterministic character n-gram vectors over folded text
(no model download, no network, no persisted state). Within each exact-phrase
tier the keyword rank and the vector rank are combined by reciprocal rank
fusion (RRF), so an exact normalized phrase match still ranks first.
"""

import math
import re
import zlib
from collections import Counter
from itertools import groupby

from app.services.rag_lite.vocabulary import folded

DIMENSIONS = 4096
NGRAM_SIZES = (3, 4, 5)
RRF_K = 60


def embed(text: str) -> dict[int, float]:
    words = re.findall(r"[a-z0-9]+", folded(text))
    counts: Counter[int] = Counter()
    for word in words:
        padded = f" {word} "
        for size in NGRAM_SIZES:
            for start in range(max(len(padded) - size + 1, 1)):
                gram = padded[start : start + size]
                counts[zlib.crc32(gram.encode()) % DIMENSIONS] += 1
    vector = {key: 1 + math.log(value) for key, value in counts.items()}
    norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
    return {key: value / norm for key, value in vector.items()}


def cosine(left: dict[int, float], right: dict[int, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


def rerank(ranked: list, question: str) -> list:
    """Reorder keyword-ranked rows ``(phrase_match, score, doc, chunk)``."""
    if len(ranked) < 2:
        return ranked
    query = embed(question)
    result = []
    for _, tier in groupby(ranked, key=lambda row: row[0]):
        rows = list(tier)
        similarity = [cosine(query, embed(row[3]["text"])) for row in rows]
        vector_rank = {
            index: rank
            for rank, index in enumerate(
                sorted(range(len(rows)), key=lambda i: (-similarity[i], i)), 1
            )
        }
        fused = sorted(
            range(len(rows)),
            key=lambda i: (
                -(1 / (RRF_K + i + 1) + 1 / (RRF_K + vector_rank[i])),
                i,
            ),
        )
        result.extend(rows[i] for i in fused)
    return result
