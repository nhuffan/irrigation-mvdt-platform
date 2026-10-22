"""Execute the separate fixed POC cohort. No participant-study templates are read/written."""

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, payload=None):
    request = Request(
        url,
        data=json.dumps(payload).encode() if payload else None,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=20) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-base", default="http://localhost:3000")
    parser.add_argument(
        "--cases", type=Path, default=ROOT / "research/ai-poc/rag_lite_eval_cases.csv"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    args = parser.parse_args()
    if args.output is None:
        stamp = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y%m%dT%H%M%S%f")
        args.output = ROOT / f"research/ai-poc/rag_lite_eval_results_{stamp}.csv"
    if args.output.exists():
        parser.error(
            "Results already exist; choose a new --output path to preserve measurements"
        )
    rows = list(csv.DictReader(args.cases.open()))
    results, pdfs, pages = [], {}, {}
    for row in rows:
        body = {
            key: row[key] for key in ["question", "reservoir_id", "query_type", "mode"]
        }
        body.update(
            asset_id=row["asset_id"] or None,
            all_authorized_docs=row["all_authorized_docs"] == "true",
            top_k=5,
        )
        if row["attribute_key"]:
            body["attribute_key"] = row["attribute_key"]
        start = perf_counter()
        value = json.loads(fetch(args.web_base + "/api/rag-lite", body))
        latency = (perf_counter() - start) * 1000
        citations = value["citations"]
        hit = any(
            (
                not row["expected_record_id"]
                or c["record_id"] == row["expected_record_id"]
            )
            and (
                not row["expected_document_id"]
                or c["document_id"] == row["expected_document_id"]
            )
            and (not row["expected_page"] or str(c["page"]) == row["expected_page"])
            for c in citations
        )
        expected_hit = bool(row["expected_record_id"] or row["expected_document_id"])
        expected_rank = (
            next(
                (
                    rank
                    for rank, c in enumerate(citations, 1)
                    if (
                        not row["expected_record_id"]
                        or c["record_id"] == row["expected_record_id"]
                    )
                    and (
                        not row["expected_document_id"]
                        or c["document_id"] == row["expected_document_id"]
                    )
                    and (
                        not row["expected_page"]
                        or str(c["page"]) == row["expected_page"]
                    )
                ),
                None,
            )
            if expected_hit
            else None
        )
        exact = None
        if row["expected_value"]:
            exact = any(
                (
                    Decimal(str(c["value_number"])) == Decimal(row["expected_value"])
                    if c["value_number"] is not None
                    else c["value_text"] == row["expected_value"]
                )
                and c["unit"] == row["expected_unit"]
                and c["asset_id"] == row["asset_id"]
                and c["record_id"] == row["expected_record_id"]
                for c in citations
            )
        valid = 0
        for citation in citations:
            url = citation["url"]
            assert url.startswith(("/assets/", "/documents/")) and "://" not in url
            if url not in pages:
                pages[url] = fetch(args.web_base + url)
            source_url = f"/data-sources/{citation['source_id']}/documents"
            if source_url not in pages:
                pages[source_url] = fetch(args.web_base + source_url)
            if citation["document_id"]:
                doc_id = citation["document_id"]
                if doc_id not in pdfs:
                    pdfs[doc_id] = fetch(
                        args.web_base + f"/api/media/documents/{doc_id}"
                    )
                data = pdfs[doc_id]
                assert hashlib.sha256(data).hexdigest() == citation["checksum_sha256"]
                reader = PdfReader(io.BytesIO(data))
                page = citation["page"]
                assert 1 <= page <= len(reader.pages)
                original = " ".join(
                    (reader.pages[page - 1].extract_text() or "").split()
                )
                assert citation["excerpt"] in original
            valid += 1
        passed = (
            value["status"] == row["expected_status"]
            and (hit if expected_hit else not citations)
            and exact is not False
        )
        results.append(
            {
                "case_id": row["case_id"],
                "status": value["status"],
                "passed": passed,
                "latency_ms": round(latency, 3),
                "hit_at_5": hit if expected_hit else "",
                "exact_value_unit_asset": exact if exact is not None else "",
                "citation_count": len(citations),
                "resolvable_citations": valid,
                "citation_ids": "|".join(c["citation_id"] for c in citations),
                "hit_at_1": expected_rank == 1 if expected_hit else "",
                "hit_at_3": expected_rank is not None and expected_rank <= 3
                if expected_hit
                else "",
                "returned_pdf_pages": "|".join(
                    str(c["page"]) for c in citations if c["document_id"]
                ),
            }
        )
    with args.output.open("x") as output:
        writer = csv.DictWriter(
            output, fieldnames=list(results[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(results)
    print(
        json.dumps(
            {
                "cases": len(results),
                "passed": sum(r["passed"] for r in results),
                "citations": sum(r["citation_count"] for r in results),
                "resolvable_citations": sum(r["resolvable_citations"] for r in results),
                "latency_min_ms": min(r["latency_ms"] for r in results),
                "latency_max_ms": max(r["latency_ms"] for r in results),
            },
            indent=2,
        )
    )
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
