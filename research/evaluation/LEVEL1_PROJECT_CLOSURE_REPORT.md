# Level 1 project closure assessment

**Assessment: `LEVEL1_ACCEPTED_WITH_DISCLOSED_LIMITS`.** Version `LEVEL1-SOURCE-FIRST-v1`, assessed 21 October 2026. This is a source-backed asset/document-information prototype; it is not an Operational Digital Twin. The data audit, production build, 37 HTTP checks and all seven recorded browser plan flows pass within the disclosed environment and evidence scope. Four principal end-to-end flows were observed: asset/provenance, PDF, reference GIS and LOCAL representative 3D. This is AI-operated software acceptance, not an independent domain signature or Operational Digital Twin acceptance.

## Current version and evidence

Software commit `414e9a3f3f2c0c49497b79e7b5a788538a214fda` on main; production build `7Z_kspVyTm0sDO5k05tyy`. Initial working tree already contained a STAGE_OUTPUTS.md edit, preserved. Initial tracked-worktree fingerprint `c2c2c223041934f02bf7138bc21a1742ad3e3c75ab721fe78b404833789266d3`. No application, schema, controlled review or research-data edit was required by the observed checks. This stage adds the assessment, comparison, runbook and evidence package.

DB/media fingerprint `3e1004b5a6b0b68c4ed990bdf8a3d473218b100175f03a069bc1d105e2aa334c`. DB capture SHA `a315cb4337bcfaaac3af594de29792048b79838d47d1b3a6a36d81a55d5c5ad3`; API capture SHA `3945517e6d73f5b8fd2c6401d4b7cad6d71379afd212089cd1a7420badc9b8f8`. Exact measurement time: `2026-10-21T07:09:51.095673+00:00`. The 22 July 2026 scope reference is a mixed historical/design boundary, not a certification date: unknown source dates are not inferred before it.

Private evidence is retained in `evidence/LEVEL1-CLOSURE/`, protected by the existing .gitignore. [Acceptance](level1_acceptance.csv), [paper delta](post_paper_delta.csv), [presentation](LEVEL1_POST_PAPER_IMPROVEMENTS_PRESENTATION.md), [current project demo](../../DEMO.md). The private `level1_snapshot_manifest.json` binds exact files, commands, media hashes and the content-addressed presentation evidence snapshot; it does not label DT-R1 FROZEN.

## Measured availability

| Indicator | Current measured value | Meaning |
|---|---:|---|
| Primary / supplementary component assets | 4 / 6 | 10 distinct UUIDs; primary research denominator stays 4 |
| Direct historical L2 | 44 | 17 primary +27 component; not 44 required MAIM fields |
| Primary direct L2: DAM / SPILLWAY / INTAKE / MGMT | 7 / 10 / 0 / 0 | Child attributes never counted as direct parent claims |
| Descendant L2: INTAKE / MGMT | 18 / 9 | C01/02/03:6 each; OFFICE 5/SAIL 1/DINING 3 |
| Formal primary claims / supplementary child L2 | 25 / 27 | Formal 25=17 technical+6 documents+1 model+1 link |
| Controlled logical sources / registered DB sources | 22 / 21 | 46 indexed evidence representations are a different grain |
| Expected-file source entries | 17 | File expectation, not retention or authority |
| Distinct reviewed retained PDF hashes / asset-document links | 6 / 2 | Two distinct linked documents; all 6 retained byte hashes rechecked |
| Navigation reference locations / canonical geometry | 2 / 0 | DAM/SPILLWAY references only; no surveyed accuracy claim |
| Verified current condition / performed O&M records | 0 / 0 | Absence of admitted evidence, not absence of real-world work |
| LOCAL models / representative model-asset links | 1 / 1 | MGMT parent, G-No_Name_008; no specific child-building identity |
| Canonical source dates known | 0 of 21 registered | Partial document/review years do not replace source_date |

All 44 technical UUID/value/unit/source/EVID/locator pairs match the captured DB/API/controlled index. All ten asset IDs and six parent joins match. The 25-indicator stage-local query replays from the archived capture; no live import occurs. Per-asset availability is in `level1_current_baseline.json`; exact formulas/commands are in `level1_metric_dictionary.md` and `replay_captured_baseline.py`. Required MAIM applicability/completeness denominators remain null pending real domain review.

## Observed checks and acceptance

Fresh `pnpm --filter web build` completed successfully, including TypeScript and production route generation. The actual production server passed **37 distinct HTTP checks**: overview/map/methodology, ten asset pages, six document pages, six PDF previews and six downloads with exact hashes, 3D deep-link route and GLB bytes, and nonexistent asset/document 404s. The final record includes 50 HTTP transactions because 13 header assertions were rerun after correcting the test harness's header-name case handling. This was a harness correction, not an application regression or source-code fix.

The actual production `/api/research-summary` reports `RECORD_READBACK_MATCH` for controlled and completion alignment and `AVAILABLE` quantitative data. Checked private reviewer name/path/receipt/storage-key tokens are absent from this summary. This is a scoped response check, not a comprehensive security audit; the intentionally public browser map key is not a server secret and remains configured in ignored .env.local.

| Criterion | Status | Observed evidence and limit |
|---|---|---|
| L1-A identity/hierarchy | PASS | Exact ten UUIDs/six parent joins; registry search C01 and reference filter; direct/descendant hierarchy shown |
| L1-B technical/source traversal | PASS | All 44 data bindings checked; actual DAM/SPILLWAY/C01 provenance disclosures and source-to-document navigation |
| L1-C document retrieval | PASS | Chrome PDF page 9/51 rendered; actual download 4,701,990 bytes matches retained SHA; in-app iframe blank disclosed |
| L1-D bounded spatial reference | PASS | SPILLWAY selection and DAM deep link; source/legend/OSM attribution; injected basemap failure preserves markers/panel |
| L1-E representative 3D interaction | PASS | Actual roof pick → MGMT/G-No_Name_008 amber highlight; clear/reset/entire model/deep link; localhost origin |
| L1-F honest missingness | PASS | Expanded O&M sections empty; MAIM formal denominators unavailable; no invented geometry/events |
| L1-G reproducible evidence | PASS | 25 metric replay, 17 byte-identical exporter artifacts, exact browser/media fingerprints and content-addressed evidence package |

[Seven new captures and their manifest](../../docs/paper_img/level1-current/README.md) are separate from historical paper figures. Private `browser/browser-states.json` retains 24 observed states, `browser/captures.json` binds 25 private captures, and `browser/browser-smoke-results.json` links all seven plan flows to observations. Table 6 exported by the existing exporter retains its historical review dates and scope; its old PASS rows were not used to manufacture this new assessment. AI software/data audit is not a researcher signature or domain/independent acceptance.

### Disclosed execution limits

- **PDF:** the in-app browser showed a blank PDF iframe. The same actual PDF rendered in Chrome, including page 9 with 200 bar / 250 mm / 125 mm / 4,650 mm source values; the actual Download click completed and its SHA matched. Chrome is the observed PDF demo environment. Cross-browser PDF preview is not certified.
- **Origin:** client model-link requests failed on `http://127.0.0.1:3000`; the configured API CORS origin is `http://localhost:3000`, on which the LOCAL model and selection worked. Use localhost for the client demo. No allowlist or security policy was weakened.
- **Fallback:** an isolated, user-authorized Playwright headless run deliberately aborted 25 OSM tile requests. The basemap-unavailable notice appeared and the correct SPILLWAY marker/panel remained usable. This is fault injection, not a report of an actual provider outage; screenshot is labeled accordingly.
- **Scope:** browser interaction sampled DAM, SPILLWAY, C01 and MGMT; all 44 row bindings and six retained PDF byte hashes were separately checked. This is not exhaustive device/performance testing, geometry surveying, current-condition validation or full model semantics. Raw survey statistics remain unverified.

Browser access was initially unavailable; the initial NOT_TESTED matrix is retained privately under `browser/initial-*`. After the user enabled Browser use and the app session refreshed, IAB/Chrome became available and the new evidence was collected. An earlier interrupted headless opening produced no completed observation and is excluded from acceptance. The only later Playwright fault-injection result was completed and verified.

## Full Stage5B remains independent

Unmodified `STAGE-5B-MC/ROLE_SCOPED-v1` still returns exit 2 / NOT_READY: **33 PASS,3 N/A,9 PENDING,2 FAIL**,23 diagnostic strings across 47 declared gates. Eleven unresolved gate IDs: MC_MAIM, MC_APPROVAL, CASE_maim, CASE_source_authority, CASE_geometry, CASE_checkpoint_a, CASE_checkpoint_b, CASE_checkpoint_c, CASE_checkpoint_d, F02, F05. No new gate closed. F02/F05 remain FAIL; the new representative-object interaction supplies separate Level 1 evidence, without changing historical F15 or establishing full model semantics.

Package `d97ddb9110f07ad7085be613198fb91e2158b2f038677f5f39e6082ac3deb795` and base `57cbbeac9f7582bf9f1c3293259870c47281ac13e83bc7cdfdeaf234222406ff` are preserved. The existing exact-package RESEARCHER_APPROVAL remains separate from absent DOMAIN_REVIEW/MAIM. Source ownership/authenticity and whole-corpus authority are not manufactured:17 historical AI source-layer reviews plus 5 scoped researcher reviews do not become 22 independent authority certifications. No checkpoint A–D criteria/signature or mandatory MAIM definition was backfilled.

## Architecture and replay

Next.js supplies asset-centric pages and same-origin media/summary adapters. FastAPI supplies identity, direct attributes, documents, timeline and model-link endpoints. PostgreSQL/PostGIS retains canonical relationships and empty geometry; local retained storage supplies checksum-addressed PDF/GLB bytes. Controlled review CSV/JSON binds provenance and bounded research scope. MapLibre and Cesium are presentation layers for reference navigation and LOCAL representative interaction; neither supplies surveying, live monitoring or simulation.

Use the existing private inputs and run from repository root. In the browser open `http://localhost:3000`; server bind addresses in these commands are not browser-origin choices:

```sh
pnpm --filter web build
# In separate terminals for the actual browser smoke:
cd apps/api
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# From repository root in another terminal:
pnpm --dir apps/web exec next start --hostname 127.0.0.1 --port 3000
```

Snapshot verification, also from repository root:

```sh
apps/api/.venv/bin/python research/evaluation/evidence/LEVEL1-CLOSURE/replay_captured_baseline.py
apps/api/.venv/bin/python scripts/export_methodology_dashboard.py --snapshot research/evaluation/evidence/LEVEL1-CLOSURE/db-before.json --api-readback research/evaluation/evidence/LEVEL1-CLOSURE/api-readback.json --controlled-dir research/dataset/reviewed --output research/evaluation/results/LEVEL1-CLOSURE/new-replay --public research/evaluation/results/LEVEL1-CLOSURE/new-replay/methodology.json
```

`export-replay.json` retains exact executed argv and all 17 artifact hashes; Tables 1/4/6 CSV+Markdown also match the preceding stage. `full_stage5b.command` in the baseline contains the exact unchanged compiler invocation. Never run seed commands against this research dataset to obtain a demo or replace empty states. Stop services started for the demo after use; preserve preexisting PostGIS.

## Paper, survey and evidence boundary

Read-only historical paper: `DAU_TIENG_PAPER_FINAL_EN.docx`,19 rendered pages, SHA `0fb535ba4c2408df7ecbec3141147d627ac917c44ba6cd53f8b9b49ededd9564`. Sections 2.3–2.5/3.1–3.4, Tables 1/4/5 and Figures 3/4/5 were inspected. The paper has two headings numbered 3.1; comparison rows therefore include heading/page locators. Table 1 contains inventory rows at a different scope from the explicitly evaluated 10 L2 in Table 4. Current verified identities/records prevail without modifying the historical document or importing an old INTAKE location/model link.

[The 16-row delta](post_paper_delta.csv) explains primary 10→17, separately scoped 27 child fields, sources 18→22 and expected-file 13→17. Six retained PDFs/two document edges/two references/zero canonical geometry remain unchanged. “Post-paper” means beyond the paper-reported cohort; exact publication/data-cohort chronology is not authenticated from a file timestamp.

Tables 2/3 are **SURVEY_NOT_VERIFIED**: no raw respondent workbook was found in workspace/Downloads; the maintenance workbook is unrelated to respondent statistics. Raw n is null, Mean/SD were not recomputed, and 35 responses were not assumed. Existing paper figures/capture manifests remain historical and unchanged. No new browser images were fabricated. Raw originals, API snapshots, review receipts and keys remain private/ignored; public assessment artifacts contain aggregate data and bounded evidence references.

## Service cleanup

Final verification in private `services.json` / `integrity-verification.json` confirms both task-owned API/web PIDs exited and ports 3000/8000 have no listeners. Test tabs and the isolated fallback browser are closed. Preexisting mvdt-postgis remains healthy; no volume was removed. DB rows/media hashes, all 49 controlled inputs, the public methodology JSON, historical paper images and original Word file are unchanged. Existing exact-package approval remains preserved. No commit or push was performed.
