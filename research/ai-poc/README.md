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

`POST /api/v1/experimental/rag-lite/query` accepts `question`, `reservoir_id`, exactly one of `asset_id` or `all_authorized_docs=true`, optional `query_type` (`auto`, `attribute`, `document`), `attribute_key`, `mode` and `top_k`. It returns source-backed citations and explicit limitations. `GET /api/v1/experimental/rag-lite/coverage?reservoir_id=<UUID>` reports current authorized/searchable/image-only/unavailable counts after original-byte and index checks; missing/changed files are never counted as searchable. Suggested questions expose the existing field labels, not generated answers. `auto` searches SQL first. Corpus-wide document results carry no asset attribution.

```sh
cd apps/api
uv run python -m pytest -q
uv run ruff check app/main.py app/core/config.py app/api/routes/rag_lite.py app/schemas/rag_lite.py app/services/rag_lite scripts/build_rag_lite_index.py tests/test_rag_lite*.py
cd ../..
apps/api/.venv/bin/python scripts/evaluate_rag_lite.py --output /tmp/rag-lite-evaluation-new-run.csv
pnpm --dir apps/web lint
pnpm --dir apps/web build
node --test apps/web/tests/*.test.mjs
```

The evaluator requires running enabled local services and the pinned corpus. Its default output is a new timestamped CSV; explicit output paths must not already exist. Existing measurements are never overwritten. Additional hit@1/hit@3 and returned-page columns preserve the original result columns. [Cases](rag_lite_eval_cases.csv) contain source-checked expected record/page IDs; [results](rag_lite_eval_results.csv) are written only by actual executions. They remain separate from the historical participant-study protocol.

Limits: 1,000-character questions, top-k 1–8, 25 MiB PDFs, 300 pages per PDF, 8 KiB web requests and 30 queries/minute per client host/process. This is a local retrieval-only prototype: no OCR, translation/embedding model, current-condition inference or operational advice. PDF searches require all meaningful keywords and prefer exact normalized phrases. Accent folding can still confuse words (for example, dày/đây), and paraphrases may be missed. Check original PDF pages; keyword hits and citation validity do not prove engineering correctness. Public deployment needs access controls and shared rate limits.


## 90–120 second evidence-search demonstration

Use the enabled local services and authorized corpus above; open [Evidence Search](http://localhost:3000/ai-research-preview). The interface provides retrieval evidence. `UnavailableProvider` is intentional: no external model is connected, and any provider/data-transfer approval belongs to a separate stage.

1. **0:00–0:25** Choose Spillway and click the suggested design-pressure field. Inspect the exact historical **200 bar** value. Expand **Evidence details** to distinguish the reviewed record from its UNVERIFIED source and UNKNOWN authority, then follow [source details](http://localhost:3000/data-sources/fa8c5d20-e1b9-52c3-94ca-2644ef56ac82/documents).
2. **0:25–0:55** Return to search, select Spillway, and open **More search options → Show document passages only**. Search `hành trình 4650`. Open the [original manual at physical PDF page 9](http://localhost:3000/api/media/documents/6c2975db-da89-546c-b1c7-f421827c1fc2#page=9), printed page 7. The original reports 4,650 mm stroke. For `áp suất thử nghiệm`, inspect both page-10 latch and page-9 main-cylinder passages; neither should be silently discarded. Use the **Expand excerpt** and **More passages** disclosures.
3. **0:55–1:20** Choose Intake No. 1, East Canal and its suggested canal-route field. The canonical text is **Kênh Đông** (displayed with its English label). Switch to the Intake Structure parent and search `reported_canal_route`: no inherited child evidence should appear.
4. **1:20–1:40** Ask `What is the current condition?` and inspect the explicit no-evidence state with open limitations. A historical record cannot validate current condition or justify operating advice.
5. **1:40–2:00** Open **Search coverage** and explain text-searchable versus image-only originals. **All authorized PDFs** is an explicit scope change and never attributes a corpus passage to an asset. Provenance remains inspectable; no model response or engineering confidence score is fabricated.

Chrome can open the physical-page original link. The preexisting in-app PDF iframe may remain blank; use the original link or download instead of promising an embedded preview. Stop the API/frontend processes you started after the demonstration; preserve preexisting PostGIS and its volumes.

All measured corpus coverage, test outcomes, known limitations and stage results are maintained only in the root [STAGE_OUTPUTS.md](../../STAGE_OUTPUTS.md).
