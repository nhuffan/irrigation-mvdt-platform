# Experimental historical evidence search

Optional future-work preview for read-only SQL attribute lookup and local PDF keyword search. The feature defaults to OFF. It preserves reviewed provenance, exact historical values/units and parent/component scope. No external LLM adapter is connected; grounded-answer requests return `GENERATION_UNAVAILABLE` with retrieval evidence.

## Configuration

- Set `RAG_LITE_ENABLED=true` on the API to enable the preview.
- `RAG_LITE_ALLOWLIST_PATH` points to an ignored, checksum-pinned authorization file. Missing/invalid allowlists authorize no PDFs. Local indexing permission does not authorize external processing.
- `RAG_LITE_INDEX_DIR` defaults to ignored `storage/rag-lite`. The page-aware JSON index and corpus manifest are runtime files, not source artifacts.
- `RAG_LITE_MAX_CONTEXT_CHARS` defaults to 12,000. No model credentials are required.
- The web adapter uses server-only `API_BASE_URL`, falling back to the existing `NEXT_PUBLIC_API_BASE_URL`. Browser requests stay same-origin.

The allowlist format is `{"version":1,"authorization":"actual permission reference","documents":[{"document_id":"actual UUID","checksum_sha256":"actual original SHA-256"}]}`. Populate it only for specifically authorized originals. New/changed documents require an updated authorization and checksum; do not commit source text, local caches or credentials.

## Run locally

Use the existing configured database and authorization file; no migration or development seeding is required.

From `apps/api`:

```sh
export RAG_LITE_ALLOWLIST_PATH="$PWD/../../storage/rag-lite/allowlist.json"
uv run python -m scripts.build_rag_lite_index --reservoir-id 63adca21-9195-44e2-81a2-0475bd6829f3
RAG_LITE_ENABLED=true uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In another terminal from repository root:

```sh
pnpm --dir apps/web build
pnpm --dir apps/web start --hostname 127.0.0.1 --port 3000
```

Open [AI Research Preview](http://localhost:3000/ai-research-preview). Select an exact asset/component, or explicitly search all authorized documents. Use an attribute key for exact SQL lookup and source-language keywords for document search. Parent/child records are not inherited. Stop both processes with Ctrl+C; restart the API without the enable flag to disable the preview.

## API and validation

`POST /api/v1/experimental/rag-lite/query` accepts `question`, `reservoir_id`, exactly one of `asset_id` or `all_authorized_docs=true`, optional `query_type` (`auto`, `attribute`, `document`), `attribute_key`, `mode` and `top_k`. It returns source-backed citations and explicit limitations. `auto` searches SQL first. Corpus-wide document results carry no asset attribution.

```sh
cd apps/api
uv run python -m pytest -q
uv run ruff check app/main.py app/core/config.py app/api/routes/rag_lite.py app/schemas/rag_lite.py app/services/rag_lite scripts/build_rag_lite_index.py tests/test_rag_lite*.py
cd ../..
apps/api/.venv/bin/python scripts/evaluate_rag_lite.py
pnpm --dir apps/web lint
pnpm --dir apps/web build
node --test apps/web/tests/*.test.mjs
```

The evaluator requires running enabled local services and the pinned corpus. [Cases](rag_lite_eval_cases.csv) contain source-checked expected record/page IDs; [results](rag_lite_eval_results.csv) are written only by actual executions. They remain separate from the historical participant-study protocol.

Limits: 1,000-character questions, top-k 1–8, 25 MiB PDFs, 300 pages per PDF, 8 KiB web requests and 30 queries/minute per client host/process. This is a local retrieval-only prototype: no OCR, translation/embedding model, current-condition inference or operational advice. Check original PDF pages; keyword hits and citation validity do not prove engineering correctness. Public deployment needs access controls and shared rate limits.

All measured corpus coverage, test outcomes, known limitations and stage results are maintained only in the root [STAGE_OUTPUTS.md](../../STAGE_OUTPUTS.md#stage-rag-lite-poc-output--22-october-2026).
