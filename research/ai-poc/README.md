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

Follow the single [root local startup workflow](../../README.md#chạy-local), with its exact two-terminal RAG-enabled commands. The existing Next.js app on port 3000 and FastAPI app on port 8000 serve both the platform and this preview. Use the existing configured database, storage and authorization file; no migration or development seeding is required.

Keep an existing valid checksum-pinned index. Section-pinned documents require the reviewed onboarding boundaries for recovery; a generic rebuild reports `SECTION_REVIEW_REQUIRED` and leaves their cache untouched. For other authorized documents, only if the index is absent or stale, explicitly rebuild it from `apps/api` with `uv run python -m scripts.build_rag_lite_index --reservoir-id 63adca21-9195-44e2-81a2-0475bd6829f3` before enabling the preview. Do not reseed or reset the database.

Open [AI Research Preview](http://localhost:3000/ai-research-preview). Select an exact asset/component, or explicitly search all authorized documents. Use an attribute key for exact SQL lookup and source-language keywords for document search. Parent/child records are not inherited. Stop both processes with Ctrl+C; set `RAG_LITE_ENABLED=false` and restart the API to disable the preview.

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

The evaluator requires running enabled local services and the pinned corpus. Its default output is a new timestamped CSV; explicit output paths must not already exist. Existing measurements are never overwritten. Additional hit@1/hit@3 and returned-page columns preserve the original result columns. [Cases](rag_lite_eval_cases.csv) contain source-checked expected record/page IDs; [results](rag_lite_eval_results.csv) are written only by actual executions. They remain separate from the historical participant-study protocol.

Limits: 1,000-character questions, top-k 1–8, 25 MiB PDFs, 300 extracted pages per PDF (longer originals require explicit reviewed partial selection), 8 KiB web requests and 30 queries/minute per client host/process. This is a local retrieval-only prototype: no OCR, translation/embedding model, current-condition inference or operational advice. PDF searches require all meaningful keywords and prefer exact normalized phrases. A small local engineering vocabulary also matches attested concepts such as crest elevation, earthfill and bentonite core walls; the full concept must match, and explicit Vietnamese diacritics outside it remain constrained. Numbers are compared as whole literals: decimal commas with one/two fractional digits and spaced thousands are recognized; ambiguous three-digit comma forms stay literal. Original values/text are never reformatted and units are never converted. Explicitly accented query keywords constrain matches by base letters and diacritic inventory; unaccented keywords remain accent-insensitive. This removes the source-checked dày/đáy and tâm/tam collision in the fixed wall-thickness case. Missing source accents, identical diacritic inventories in different positions, and paraphrases can still cause misses or collisions. Check original PDF pages; keyword hits and citation validity do not prove engineering correctness. Public deployment needs access controls and shared rate limits.


## 4–6 minute multi-asset evidence demonstration

Use the enabled local services and retained authorized originals at [AI Research](http://localhost:3000/ai-research-preview). The selector groups parents/components while keeping exact UUID scope. The compact availability line reports live reviewed fields/searchable PDFs, with image-only, unavailable or unscoped originals when applicable; availability is not engineering validation. Source UNVERIFIED and authority/date Unknown stay distinct from reviewed records.

1. **0:00–0:55 · Main Dam: record → original.** Choose **Main Dam — Đập chính**. Under Suggested questions select the crest-elevation field: **28 m**, datum unknown. **View asset evidence** focuses record `7e6f08e6-7b86-5e24-861b-968ea40a184a`; inspect `PDF:p20:printed9:Table2:MainDam` and its source. Browser Back restores the search. Select **PDF · Dam material — vật liệu đập** and open the [historic EIA original at physical page 20](http://localhost:3000/api/media/documents/62e83ed1-2162-510a-a8ce-344a7320c8d1#page=20), printed page 9: Main Dam earthfill row, 1100 m crest length and 8 m width. Only the mapped Main Dam row/header is attributed to this asset.
2. **0:55–1:40 · Spillway: distinguish cylinders.** Select **Spillway — Tràn xả lũ**; previous references clear. In Search options choose **Document passages only**, search `áp suất thử nghiệm`: both [physical page 9](http://localhost:3000/api/media/documents/6c2975db-da89-546c-b1c7-f421827c1fc2#page=9) (main gate cylinder) and [physical page 10](http://localhost:3000/api/media/documents/6c2975db-da89-546c-b1c7-f421827c1fc2#page=10) (latch cylinder) report **270 bar**. The generic query does not choose a cylinder. This is the retained manual, not measured present pressure. `tường bentonite` stays unavailable under Spillway despite the shared EIA containing Main Dam proposals.
3. **1:40–2:45 · Intake component and parent boundary.** Choose **Intake No. 1, East Canal**. Its **Discharge** suggestion returns reviewed **93 m3/s** at normal pool, record `50476406-5a9c-51e3-85c8-3a062122333f`. **PDF · Sill elevation — cao trình ngưỡng** opens its own paragraph at [SIWRR physical page 47](http://localhost:3000/api/media/documents/224161a4-a365-51fa-8885-6b7be6d6a433#page=47). C01 embedded text spells `lư u lượng`; matching recognizes this source-attested spacing without editing it. Choose **Intake No. 3, Tan Hung Canal**: its discharge is separately **12.8 m3/s design**, record `e42a3f4d-7400-560f-a806-485d0fc104f2`, and its own paragraph on the same page reports sill **+15,75 m**. Select the **Intake Structure (parent only)** and search `cao trình ngưỡng`: no linked evidence; children are not inherited. Only physical page 47 of the 355-page original is indexed; omitted pages are not silently searched.
4. **2:45–3:40 · Independently supported building and truthful limits.** Choose **Office Building**. The water-tank suggestion gives reviewed **1500 L**, record `2f0ab345-641f-5ced-98d6-fd880a4d0777`; document mode `MÁI LỢP NGÓI` opens [office drawing physical page 10](http://localhost:3000/api/media/documents/b5258e05-2d4c-5f18-8fac-decf9e5198d3#page=10), HT.02. Existing-condition captions and repair proposals interleave in extraction: inspect the original columns; no claim of completed repair or present condition. **Sail Building** keeps its reviewed **28.76 m** floor record `676e3592-2c6a-5ca9-8993-1eb026ec35cd`, datum unverified. Its shared drawing on physical p5 has mixed text order, so it has **no reviewed PDF passages**; Office passages do not leak into Sail. Dining has three reviewed fields and one image-only original, without OCR.
5. **3:40–4:40 · Explicit corpus search, pagination and return.** Choose **All authorized PDFs** and search `thủy lực`. The scope says **no asset attribution**. Numbered pages show five passages at a time; select page 2 and inspect different original links. Open **Evidence details → Document details → Back to AI Research**: scope, keywords, mode and page 2 are restored by a fresh evidence request. The URL stores the validated request only, never cached excerpts. Reload/copying that URL also rechecks authorization and originals. Direct original PDF links open separately; close that tab to return to the existing search.
6. **4:40–5:10 · Unsupported current condition.** Select an exact asset and ask `tình trạng hiện tại`: **Outside search scope**. Historical values, proposals and source-linked passages cannot establish present condition or support an operating decision.

Free text remains available; suggestions are shortcuts to actual fields or currently matching scoped passages. Natural examples include `Intake 1 discharge`, `sill elevation`, `opening width`, `dung tích bồn nước` and `water tank capacity 1500L`. Literal values and units remain unchanged; no conversion is performed. An unambiguous different component name/code fails scope validation, rather than changing the selected asset.

The new [multi-asset cohort](rag_lite_multi_asset_cases.csv) pins original sources, record IDs/values/units, physical pages, keywords, reason codes and asset/null attribution. It runs alongside the unchanged [Main Dam cohort](rag_lite_main_dam_cases.csv) and [original fixed cohort](rag_lite_eval_cases.csv). Authorization/index/original failure paths use focused isolated API fixtures, without mutating the live corpus. These checks are implementing-agent source verification, not independent domain validation or participant-study metrics.

Search options retain detailed coverage and recovery information. A shared original with no reviewed section for this exact asset reports **No reviewed PDF passages**, separately from missing originals/index errors, image-only text and a completed no-match. Partial searches retain valid references. HTTP429/network failures expose Retry. Existing compact results, five-per-page pagination and original/record actions are preserved.

Chrome can open the physical-page original link. The preexisting in-app PDF iframe may remain blank; use the original link or download instead of promising an embedded preview. Stop the API/frontend processes you started after the demonstration; preserve preexisting PostGIS and its volumes.

All measured corpus coverage, test outcomes, known limitations and stage results are maintained only in the root [STAGE_OUTPUTS.md](../../STAGE_OUTPUTS.md).
