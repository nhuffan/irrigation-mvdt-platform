# Experimental historical evidence search

Optional research preview for read-only SQL attribute lookup and local PDF keyword search. The preview defaults to OFF. It preserves reviewed provenance, exact historical values and units, and parent/component scope. Evidence-only is the default search mode. The optional Ollama adapter uses a local model and requires a separate model-processing grant.

## Configuration

- Set `RAG_LITE_ENABLED=true` on the API to enable the preview.
- `RAG_LITE_ALLOWLIST_PATH` points to an ignored, checksum-pinned authorization file. Missing/invalid allowlists authorize no PDFs. Local indexing permission does not authorize external processing.
- `RAG_LITE_INDEX_DIR` defaults to ignored `storage/rag-lite`. The page-aware JSON index and corpus manifest are runtime files, not source artifacts.
- `RAG_LITE_MAX_CONTEXT_CHARS` defaults to 12,000. No model credentials are required.
- The web adapter uses server-only `API_BASE_URL`, falling back to the existing `NEXT_PUBLIC_API_BASE_URL`. Browser requests stay same-origin.

The allowlist format is `{"version":1,"authorization":"actual permission reference","documents":[{"document_id":"actual UUID","checksum_sha256":"actual original SHA-256"}]}`. Populate it only for specifically authorized originals. New/changed documents require an updated authorization and checksum; do not commit source text, local caches or credentials.

## Run locally

Follow the single [root local startup workflow](../../README.md#chạy-local), with its exact two-terminal RAG-enabled commands. The existing Next.js app on port 3000 and FastAPI app on port 8000 serve both the platform and this preview. Use the existing configured database, storage and authorization file; no migration or development seeding is required.

Keep an existing valid checksum-pinned index. Section-pinned documents require the reviewed onboarding boundaries for recovery; a generic rebuild reports `SECTION_REVIEW_REQUIRED` and leaves their cache untouched. For other authorized documents, only if the index is absent or stale, explicitly rebuild it from `apps/api` with `uv run python -m scripts.build_rag_lite_index --reservoir-id 63adca21-9195-44e2-81a2-0475bd6829f3` before enabling the preview. Do not reseed or reset the database.

Open [AI Research Preview](http://localhost:3000/ai-research-preview). Select an exact asset/component, or explicitly search all authorized documents. Use an attribute key for exact SQL lookup and source-language keywords for document search. Parent/child records are not inherited. Stop both processes with Ctrl+C; set `RAG_LITE_ENABLED=false` and restart the API to disable the preview.

## Local MCP client

From `apps/api`, run `uv sync --locked`. Configure the MCP client's command as `uv`, its arguments as `run --locked --directory /absolute/path/to/repo/apps/api python -m app.mcp.server`, and its environment with `MVDT_MCP_ENABLED=true` and `MVDT_MCP_GRANT_PATH=/absolute/path/to/ignored/host-grant.json`. The server uses the configured PostGIS, storage and RAG-lite index. The client launches the stdio process directly.

The host grant is a JSON object with `version: 1`, a real permission reference in `authorization`, `reservoir_id`, `asset_ids` and `source_ids` arrays, and `document_checksums` mapping allowed document UUIDs to original SHA-256 hashes. `allow_evidence` permits excerpts and reviewed values, while `allow_links` additionally permits relative application URLs. Both permissions default to false. Check where the MCP client sends tool output before granting it evidence text. A revoked or unreadable grant stops tool access.

List the four tools first. Use `get_asset_details` with exact reservoir and asset UUIDs, `get_document_provenance` with a granted source UUID, and `get_research_coverage` to check the available evidence. Call `search_evidence` with either that asset UUID or `all_authorized_docs=true`. A corpus-wide result has no asset attribution.

## Local grounded answers

Run a trusted Ollama daemon at `127.0.0.1:11434` with an installed local model, `OLLAMA_NO_CLOUD=1` and request-body logging disabled. Confirm cloud is disabled in the daemon startup log. Set `RAG_LITE_ENABLED=true`, `RAG_GENERATION_ENABLED=true`, `RAG_PROVIDER=ollama`, `RAG_OLLAMA_MODEL=<model:tag>` and `RAG_GENERATION_AUTHORIZATION_PATH=/absolute/path/to/ignored/model-grant.json` on the API. Use a local or otherwise access-controlled copy of the preview. [Ollama cloud settings](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features) · [Structured outputs](https://docs.ollama.com/capabilities/structured-outputs)

The separate model grant is a JSON object with `version: 1`, `authorization`, `provider: "ollama"`, `model` matching the configured tag, and `reservoir_id`. Add only granted entries to `records` (`source_id` and exact `citation_id` from an evidence-only result) or `documents` (`source_id`, `document_id` and `checksum_sha256`). A changed record fingerprint or PDF checksum requires a new grant. Keep authorizations outside Git.

The preview shows **Grounded answer** when model readiness and the reservoir grant are available. Start with **Evidence only**, then ask for an answer in the same scope and follow its citation to the record or physical PDF page. Back and reload restore the evidence search. If the model fails, the retrieval evidence remains available. The daily limit and concurrency cap apply per API worker, so use one worker for a single local quota.

## Synthetic demo corpus

`apps/api/tests/demo_corpus.py` defines a fictional **Demo Reservoir** labelled `SYNTHETIC DEMO DATA - not research evidence`: two assets (main dam and child spillway), three reviewed attributes, a deterministic four-page design PDF (English, unaccented Vietnamese and two prompt-injection probe pages) and a text-free PDF. Every value was written for this project. Tests insert the rows only inside a rolled-back transaction and write the PDFs, allowlist and index only to a temporary directory; nothing reaches the research database, `storage/` or the real allowlist, and the corpus never appears in the UI. Run `cd apps/api && uv run python -m pytest -q tests/test_demo_corpus.py`.

## Grounded-answer evaluation

- **Guardrails (no model, synthetic evidence):** `cd apps/api && uv run python -m scripts.evaluate_rag_generation` runs the 23 cases in [rag_generation_guardrail_cases.csv](rag_generation_guardrail_cases.csv) through the production `respond()` path with scripted model outputs: faithful answers, hallucinated numbers, changed units, invented citations, links/markup, present-condition/safety/advice/prediction claims, empty/malformed/timeout/error responses and prompt-injection echoes. Passages that read as instructions to an AI stay visible as evidence but are never sent to the model (R16, R22, R23). It writes a new timestamped CSV. Add `--provider ollama --model <tag>` to score a real local model on the same synthetic evidence; only cases with `expected_model_outcome` are scored then.
- **Private corpus (needs model + grant):** [rag_lite_generation_cases.csv](rag_lite_generation_cases.csv) reuses verified Main Dam/multi-asset cases in `grounded_answer` mode with `expected_answer_text`. Run it with `scripts/evaluate_rag_lite.py --cases` only when a local model and a model-processing grant for those records exist. Without a model, supported cases correctly return `GENERATION_UNAVAILABLE` with evidence and are reported as failures.
- Citation validity and these checks do not establish factual or engineering correctness; groundedness still needs human review.

## Optional hybrid re-ranking

`RAG_HYBRID_ENABLED=true` re-orders PDF passages that the keyword search already admitted, using local deterministic character n-gram vectors and reciprocal rank fusion inside each exact-phrase tier. It never adds, removes or rescopes evidence and needs no model or network. It is OFF by default: on the fixed cohorts it changed no rank (see Stage 21 in `STAGE_OUTPUTS.md`). Compare from `apps/api` with `RAG_LITE_ALLOWLIST_PATH=... uv run python -m scripts.compare_rag_hybrid --output <new.csv>`; it uses a read-only transaction.

## Optional remote MCP transport

The standalone `app.mcp.remote:app` starts with `/mcp` disabled. For an authorized deployment, configure `MVDT_MCP_REMOTE_ENABLED=true`, the exact HTTPS URL ending in `/mcp`, the trusted issuer, its RS256 PEM public key and a separate remote disclosure grant using the variables in `apps/api/.env.example`. The reverse proxy must preserve the public Host and trusted HTTPS scheme. Apply shared rate and connection limits at the proxy and keep the original-content API private. Use the issuer's current public signing key and restart the resource server after key rotation.

The identity provider must issue short-lived RS256 JWT access tokens with this URL in `aud` and limit `mvdt:read:<reservoir UUID>` to readers of that reservoir. Grant `mvdt:export:<reservoir UUID>` only to principals permitted to export excerpts and values. Export also requires `allow_evidence` in the remote disclosure grant. Remote tool responses omit original URLs. Verify TLS, identity-provider discovery, scope assignment, ingress limits and egress policy in the target environment before exposing the service. [MCP authorization specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)

## Incremental local PDF onboarding

Use the existing source and its reviewed direct asset link. The importer never creates a source, technical field, review approval or asset identity. A missing source/link requires a separate real evidence review first. Preserve the original filename and independently check the expected SHA-256. For another authorized PDF, from `apps/api`:

```sh
RAG_LITE_ALLOWLIST_PATH="$PWD/../../storage/rag-lite/allowlist.json" \
uv run python -m scripts.onboard_rag_lite \
  --file '/absolute/path/to/authorized-original.pdf' \
  --source-code EXISTING_REVIEWED_SOURCE_CODE \
  --document-code NEW_STABLE_DOCUMENT_CODE \
  --asset-id bd4aff6e-8117-426d-906e-953a2b5a4ae9 \
  --checksum-sha256 EXPECTED_ORIGINAL_SHA256 \
  --output /tmp/onboarding-dry-run-new.json
```

This is a **dry-run by default**, with no database, original, authorization or index writes. It reports stable identity, imported/skipped/reindexed intent, physical pages/chunks and per-asset coverage as JSON. If the exact original is not already allowlisted, it fails closed: only add `--authorize --authorization-reference 'actual human permission reference'` when that permission already exists. Missing/invalid authorization files and changed originals are errors. To apply the reviewed selection, repeat the command with `--apply` and a different, unused output path. Repeating an unchanged import reports `SKIPPED`; codes/checksums cannot silently replace another document. Source status, authority, dates and existing reviewed fields stay unchanged.

A source used by multiple assets requires explicit section boundaries. Add repeated `--section 'PHYSICAL_PAGE|ASSET_UUID|EXACT_START_TEXT|EXACT_END_TEXT'` and `--scope-review 'actual boundary-review reference'`; leave the last part empty only for page end. Every boundary must occur uniquely in that original page, and every asset must already have a reviewed direct source link. Mapped sections constrain selected-asset retrieval; unmapped report content remains available **only in explicit corpus mode**. This is a document-section review, never a domain/engineering attestation. A five-page document wholly supported at one asset's actual scope can remain at that scope; do not invent component boundaries.

For batches, `--manifest /absolute/path/selection.json --document-code CODE_A --document-code CODE_B` selects only named entries. The manifest is `{ "documents": [{ "file": "...", "source_code": "...", "document_code": "...", "asset_ids": ["..."], "checksum_sha256": "...", "sections": [{"page": 1, "start": "...", "end": "...", "asset_ids": ["..."]}], "scope_review": "..." }] }`. No DB-row or allowlist/cache editing is required. Only selected indexes and manifest entries are replaced, with authorization pins written last and restored on commit failure. Image-only PDFs remain image-only; no OCR or external processing is performed. The 25 MiB original-file limit still applies. For a longer original, add repeated `--include-page PHYSICAL_PAGE` flags or manifest `included_pages: [47]` alongside the reviewed sections. This opt-in partial profile extracts at most 300 selected pages, preserves the full original checksum/page count and physical page IDs, and reports processed/omitted pages. Unprocessed pages are unknown and unavailable even in corpus mode; unmapped text on processed pages remains corpus-only. Selection, scope and extraction completeness are authorization-pinned. A generic rebuild cannot expand it.

## API and validation

`POST /api/v1/experimental/rag-lite/query` accepts `question`, `reservoir_id`, exactly one of `asset_id` or `all_authorized_docs=true`, optional `query_type` (`auto`, `attribute`, `document`), `attribute_key`, `mode` and `top_k`. For retrieval-only numbered pages, send both `page` (1–10000) and `page_size` (1–20); the UI uses 5 per page. The response includes `pagination` with current page, page size, total matched references and total pages. Each page recomputes the same ranking after current authorization/original-byte checks; requests without these fields preserve the existing `top_k` contract. It returns source-backed citations and explicit limitations. `GET /api/v1/experimental/rag-lite/coverage?reservoir_id=<UUID>` reports current authorized/searchable/image-only/unavailable counts after original-byte and index checks; missing/changed files are never counted as searchable. Suggested questions expose all available reviewed-field labels (up to eight) plus up to three PDF topics validated against current authorized, asset-scoped text. A PDF suggestion selects document-only mode; pagination and retries retain that mode. They are retrieval shortcuts, not generated answers. `auto` searches SQL first. Corpus-wide document results carry no asset attribution.

```sh
cd apps/api
uv run python -m pytest -q
uv run ruff check app/main.py app/core/config.py app/api/routes/rag_lite.py app/schemas/rag_lite.py app/services/rag_lite scripts/build_rag_lite_index.py tests/test_rag_lite*.py
cd ../..
apps/api/.venv/bin/python scripts/evaluate_rag_lite.py --output /tmp/rag-lite-evaluation-new-run.csv
apps/api/.venv/bin/python scripts/evaluate_rag_lite.py --cases research/ai-poc/rag_lite_main_dam_cases.csv --output /tmp/rag-lite-main-dam-new-run.csv
# Respect the shared 30-query/minute limit between cohorts.
apps/api/.venv/bin/python scripts/evaluate_rag_lite.py --cases research/ai-poc/rag_lite_multi_asset_cases.csv --output /tmp/rag-lite-multi-asset-new-run.csv
pnpm --dir apps/web lint
pnpm --dir apps/web build
node --test apps/web/tests/*.test.mjs
```

The evaluator requires running enabled local services and the pinned corpus. Its default output is a new timestamped CSV. Choose a fresh path for each run. For grounded-answer cases, use an optional `expected_answer_text` column to check a required phrase alongside the expected record or page. The evaluator also checks that an answered response binds every inline citation to the returned citations. Review all other generated claims against the cited source. [Cases](rag_lite_eval_cases.csv) contain source-checked expected record/page IDs and [results](rag_lite_eval_results.csv) are measured runs, separate from the historical participant study.

Limits include 1,000-character questions, top-k 1–8, 25 MiB PDFs, at most 300 extracted pages per PDF, 8 KiB web requests and 30 queries/minute per client host/process. Longer originals require explicit reviewed partial selection. Search and optional generation are for historical or reference evidence. PDF searches require all meaningful keywords and prefer exact normalized phrases. A small engineering vocabulary also matches attested concepts such as crest elevation, earthfill and bentonite core walls. Full concepts and explicitly accented keywords constrain matches. Numbers are compared as whole literals, including decimal commas with one or two fractional digits and spaced thousands. Ambiguous three-digit comma forms stay literal. Missing source accents, identical diacritic inventories in different positions, and paraphrases can still cause misses or collisions. Check the original PDF pages and preserve original units. Public deployment needs access controls and shared rate limits.


## Project demonstration

The single whole-project presenter route is maintained in [root DEMO.md](../../DEMO.md). Rehearse its current asset scopes, record values and physical-page links against the authorized local corpus before presenting. The live availability line describes evidence availability, not engineering validation; source UNVERIFIED and unknown authority/date remain distinct from reviewed records.

## Evidence scope and recovery

Free text remains available; suggestions are shortcuts to actual fields or currently matching scoped passages. Natural examples include `Intake 1 discharge`, `sill elevation`, `opening width`, `dung tích bồn nước` and `water tank capacity 1500L`. Literal values and units remain unchanged; no conversion is performed. An unambiguous different component name/code fails scope validation, rather than changing the selected asset.

The new [multi-asset cohort](rag_lite_multi_asset_cases.csv) pins original sources, record IDs/values/units, physical pages, keywords, reason codes and asset/null attribution. It runs alongside the unchanged [Main Dam cohort](rag_lite_main_dam_cases.csv) and [original fixed cohort](rag_lite_eval_cases.csv). Authorization/index/original failure paths use focused isolated API fixtures, without mutating the live corpus. These checks are implementing-agent source verification, not independent domain validation or participant-study metrics.

Search options retain detailed coverage and recovery information. A shared original with no reviewed section for this exact asset reports **No reviewed PDF passages**, separately from missing originals/index errors, image-only text and a completed no-match. Partial searches retain valid references. HTTP429/network failures expose Retry. Existing compact results, five-per-page pagination and original/record actions are preserved.

Chrome can open the physical-page original link. The preexisting in-app PDF iframe may remain blank; use the original link or download instead of promising an embedded preview. Stop the API/frontend processes you started after the demonstration; preserve preexisting PostGIS and its volumes.

All measured corpus coverage, test outcomes, known limitations and stage results are maintained only in the root [STAGE_OUTPUTS.md](../../STAGE_OUTPUTS.md).
