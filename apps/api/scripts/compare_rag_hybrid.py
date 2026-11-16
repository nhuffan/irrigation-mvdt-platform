"""Compare keyword vs hybrid ranking in-process on the fixed RAG-lite cohorts.

Uses a READ ONLY database transaction, the configured storage, allowlist and
existing index. Nothing is written except the new comparison CSV. Each case is
retrieved twice (``rag_hybrid_enabled`` off/on); the evidence set must be
identical and only its order may differ.
"""

import argparse
import csv
import json
from pathlib import Path

from app.core.config import settings
from app.db.session import read_only_session
from app.schemas.rag_lite import RagQuery
from app.services.rag_lite.retriever import retrieve
from app.services.storage_service import get_storage

ROOT = Path(__file__).resolve().parents[3]
COHORTS = [
    ROOT / "research/ai-poc/rag_lite_eval_cases.csv",
    ROOT / "research/ai-poc/rag_lite_main_dam_cases.csv",
    ROOT / "research/ai-poc/rag_lite_multi_asset_cases.csv",
]


def expected_rank(row, citations):
    for rank, c in enumerate(citations, 1):
        if (
            (
                not row["expected_record_id"]
                or str(c.record_id) == row["expected_record_id"]
            )
            and (
                not row["expected_document_id"]
                or str(c.document_id) == row["expected_document_id"]
            )
            and (not row["expected_page"] or str(c.page) == row["expected_page"])
        ):
            return rank
    return None


def run(db, storage, row, hybrid):
    settings.rag_hybrid_enabled = hybrid
    body = {
        "question": row["question"],
        "reservoir_id": row["reservoir_id"],
        "asset_id": row["asset_id"] or None,
        "all_authorized_docs": row["all_authorized_docs"] == "true",
        "query_type": row["query_type"],
        "page": 1,
        "page_size": 20,
    }
    if row["attribute_key"]:
        body["attribute_key"] = row["attribute_key"]
    return retrieve(db, storage, settings, RagQuery(**body))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new path")
    storage = get_storage()
    rows, results = [], []
    for path in COHORTS:
        rows += [(path.stem, row) for row in csv.DictReader(path.open())]
    with read_only_session() as db:
        for cohort, row in rows:
            off = run(db, storage, row, False)
            on = run(db, storage, row, True)
            same_set = {c.citation_id for c in off.citations} == {
                c.citation_id for c in on.citations
            } and (off.pagination and off.pagination.total_results) == (
                on.pagination and on.pagination.total_results
            )
            expected = bool(row["expected_record_id"] or row["expected_document_id"])
            ranks = [
                expected_rank(row, r.citations) if expected else None for r in (off, on)
            ]
            results.append(
                {
                    "cohort": cohort,
                    "case_id": row["case_id"],
                    "candidates": off.pagination.total_results
                    if off.pagination
                    else len(off.citations),
                    "same_evidence_set": same_set,
                    "same_status_reasons": (off.status, off.reason_codes)
                    == (on.status, on.reason_codes),
                    "keyword_rank": ranks[0] or "",
                    "hybrid_rank": ranks[1] or "",
                }
            )
    settings.rag_hybrid_enabled = False
    with args.output.open("x", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(results[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(results)

    def metrics(key):
        ranked = [
            r[key] for r in results if r["keyword_rank"] != "" or r["hybrid_rank"] != ""
        ]
        scored = [r[key] for r in results if r["keyword_rank"] != ""]
        return {
            "hit@1": sum(rank == 1 for rank in scored),
            "hit@3": sum(rank != "" and rank <= 3 for rank in scored),
            "mrr": round(
                sum(1 / rank for rank in ranked if rank) / max(len(scored), 1), 4
            ),
            "cases": len(scored),
        }

    summary = {
        "cases": len(results),
        "evidence_set_unchanged": sum(r["same_evidence_set"] for r in results),
        "status_and_reasons_unchanged": sum(r["same_status_reasons"] for r in results),
        "keyword": metrics("keyword_rank"),
        "hybrid": metrics("hybrid_rank"),
        "changed_rank": [
            (r["case_id"], r["keyword_rank"], r["hybrid_rank"])
            for r in results
            if r["keyword_rank"] != r["hybrid_rank"]
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["evidence_set_unchanged"] == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
