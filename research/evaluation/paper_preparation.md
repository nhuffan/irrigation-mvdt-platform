# Paper figures, tables and reproducible presentation state

Open the private `research/evaluation/results/paper/index.html` to browse six software screenshots, six diagram PNGs/SVGs, five CSV/Markdown tables and captions. `figure_state.json` binds the software commit, local capture date, reviewed package fingerprint, DB snapshot and provenance sidecar checksum. `package_manifest.json` hashes the outputs. This is a presentation snapshot, never a DT-R1 research freeze.

## Technical provenance UI

The technical API response now includes nullable `reviewed_provenance`. The UI shows level, source code, evidence ID, exact locator and reviewed authority alongside the existing value/unit/status. Missing metadata renders Unavailable, never an inferred level from VERIFIED status.

By default the API reads `storage/reviewed_provenance.json`; `REVIEWED_PROVENANCE_PATH` can override this private deployment file. Version 1 contains `records` keyed by record UUID. Each entry has `record` with exactly id, asset_id, source_id, attribute_key, attribute_label, value_number, value_text, unit and verification_status; `provenance` contains verification_level, source_code, evidence_id, source_locator, authority, reviewer and reviewed_at. Every binding field and the current source code must match, otherwise metadata is omitted. The file is trusted reviewed configuration, not an independent signature/authenticity check. Refresh it after changing controlled reviews; keep its hash in the presentation manifest.

The current private export audit joins the imported technical batch provenance, candidate verification log and source-role review to exact API records. Its script and resulting hash are retained under `evidence/PAPER/`. No DB schema or engineering value was changed; no private source files are committed.

## Reproduction and interpretation

1. Restore the referenced private reviewed inputs, DB/media and matching sidecar; check hashes before starting services.
2. Run normal API/web commands from the project README. Record preexisting services and stop only task-started services afterward.
3. Use the RS dataset scope. Capture registry, GIS context, DAM provenance, stored PDF preview, MGMT LOCAL GLB deep link and the real O&M state. Do not add records to improve screenshots.
4. The private `evidence/PAPER/build_artifacts.py` regenerates tables and diagram assets from the archived DB and reviewed CSVs using bundled Pillow. `assemble_package.py` assembles the figures/captions/index. Preserve the source snapshot and run in the referenced project; update the figure state and hashes for any new capture, never overwrite a historical claim silently.
5. Recompute table totals independently: four RS targets, three technical records, zero scoped O&M, five distinct reviewed documents across source claims, one representative model link; 17 controlled sources and 12 expected files. Do not sum per-asset document counts to infer unique files without deduplication.
6. Rerun formal readiness with the same manifest and a fresh output directory. New figures do not turn F02/F05 into PASS or establish full functional regression. The historical functional matrix remains unchanged.

The GIS diagram is explicitly a conditional workflow, with QGIS preparation still pending for research geometry. LOCAL model selection is representative only; side-panel mapping does not imply object highlighting or full semantic decomposition. The source database may retain UNVERIFIED status even when a bounded field/source-role review is SUPPORTING; display these distinctions rather than silently rewriting source authority.

The remaining methodological/domain approvals are documented in the package closure report. An actual as-of boundary cannot be inferred from the screenshot date. The initial paper-preparation stage did not add a summary card; the subsequent PAPER-UI-GIS stage adds API-derived scope totals as described below.

## Interactive asset explorer (PAPER-UI-GIS)

The reservoir Assets section now shares selection across registry, map and evidence panel. `/map?asset=<UUID>` loads the asset's reservoir and opens its panel; `&paper=1` simplifies presentation without changing values, scope labels or missingness. The selected asset ID is synchronized through browser history. Geometry filters and 3D filters affect visible rows and map features; summary totals describe the full selected dataset scope. A selected asset excluded by a filter remains explicitly identified in the panel.

Counts use existing API endpoints. Failed sections report Unavailable, not zero. Technical preview contains at most three records with explicit reviewed provenance; VERIFIED alone does not imply L2. O&M counts include only VERIFIED timeline events, and current condition uses the existing verified-current-condition endpoint. Document counts are API-linked documents, not the separate source-claim coverage metric in paper table T1. 3D actions use actual model/object links. No schema migration or research import is involved.

Point, line and polygon selection uses GeoJSON property IDs via `promoteId` so UUID feature-state highlighting works. NULL geometry generates no feature. Controlled child assets use the same rendering and parent link; no special component names or coordinates are embedded in UI logic.

`pnpm --dir apps/web test:explorer` runs the state/filter/provenance/count tests. Browser smoke additionally checks registry/map selection, deep links, Back, layer filters, real action targets and identical panel/summary content with paper mode on/off. Existing DEV geometry is used only to test interaction mechanics, never as RS evidence.

The updated private `figure_state.json` uses schema version 2: `capture_sets` stores each snapshot and `figures` assigns every PNG to its actual capture set. Only S1/S2 were recaptured for this UI stage; S3–S6 and diagrams retain their original state. The previous package is archived under `evidence/PAPER-UI-GIS/previous-paper/`. Rehash `package_manifest.json` after changing outputs; do not stamp older figures with a new software commit or capture date.

### PAPER-GIS-VISUAL capture

The asset map uses OpenStreetMap standard raster tiles with visible attribution, ordinary browser caching and viewport-only requests. See [OSMF tile policy](https://operations.osmfoundation.org/policies/tiles/); no tile archive/offline download is provided. The raster source is independent of the local style and asset/context layers. Raster errors or a pending-source timeout show `Basemap unavailable`; network-outage browser testing remains for consolidated validation.

Context is the existing registry center/label plus basemap geography, not a new controlled reservoir outline. Camera overview at zoom 10 is a navigation view, not an asserted reservoir boundary. Reference focus caps at zoom 11, verified geometry at 14. Reference rings/labels remain distinct; a top selection halo does not promote verification. Missing locations return to context with a warning. Paper mode puts the map before the registry and retains attribution, legend, panel and limitations.

S2 was recaptured with the reference marker selected, popup closed and one zoom-out step to show the reservoir surroundings. S1 and other figures retain their previous capture states; read per-figure `capture_set` in `figure_state.json`. Basemap labels and context never contribute to F02 or completeness metrics.


## PAPER-UI-CLEAN-COMPLETE presentation and current paper figures

Software snapshot: `c6477f4`. Presentation aliases are keyed by controlled asset code: Đập chính — Main Dam; Tràn xả lũ — Spillway; Công trình lấy nước — Intake Structure; Nhà quản lý/vận hành — Management / Operations Building. Canonical DB names/IDs and joins are unchanged. Asset, record, document, source and model identifiers remain copyable in keyboard-accessible native details, closed by default. The browser's native PDF toolbar can show a transient blob identifier; application document headings use the real filename.

Asset Detail uses real Components beside Properties and stacks below 900px; no components are invented. Reusable coverage lists Identity, Location, Technical, Condition, Inspection, Repair, Maintenance, Documents and 3D. Successful empty responses and unavailable requests remain distinct; Reference never becomes Verified; no synthetic score. Identity is Available for REGISTERED API records; the API does not expose the separate researcher identity-review decision, so the UI does not infer it. Table 2 separately reports that controlled review.

Sources & Evidence deduplicates technical sources by source ID and distinguishes reference location, linked files, verified O&M and representative model links. Linked file counts are UI counts, not paper source-coverage denominators. Bound reviewed provenance supplies L2; record VERIFIED status alone never supplies a level. O&M empty state means no verified record, not no maintenance activity. 3D retains LOCAL and representative-only disclosure.

### Capture and manuscript mapping

All S1–S7 were recaptured because their visible UI changed. Exact URLs, viewport sizes, capture date and software commit are in the private `figure_state.json` capture set `paper_ui_clean`. New screenshots alone receive that capture set; old diagram capture sets remain intact. Previous paper package is retained under `evidence/PAPER-UI-CLEAN/previous-paper`. S1 uses normal RS-filtered registry; S2/S3/S5/S6/S7 use paper mode; S4 uses the actual PDF preview. S5 uses the preexisting configured localhost:3000 origin; other views use the task's production preview at 3100. The API rejected 3100 model requests by CORS, so it was not reconfigured merely for capture.

| Screenshot / artifact | State and paper use |
|---|---|
| S1 | `/map?asset=<DAM>#assets`, four RS names, selected DAM; §4.2 Hình 6 current panel A |
| S2 | `/map?paper=1&asset=<SPILLWAY>#selected-asset-panel`, popup closed, reference halo, OSM attribution/scale/legend; §3.4 Hình 3 left |
| S3 | `/assets/<DAM>?paper=1#technical`, three historical L2 records; optional §4.2, supporting evidence |
| S4 | `/documents/<retained-PDF>`, meaningful filename and real PDF; supporting evidence |
| S5 | `/reservoirs/<reservoir>/3d?paper=1&model=<legacy-model>&object=<reviewed-object>`, LOCAL MGMT representative selection; Hình 3 right and Hình 6 current C |
| S6 | `/assets/<DAM>?paper=1#timeline`, honest verified-empty state; private supporting evidence |
| S7 | `/assets/<DAM>?paper=1#coverage`, coverage plus source/evidence summary; §4.3 and Hình 6 current B |
| Hinh_1 | Authored phased research architecture for §3.1, not browser capture |
| Hinh_2 | Authored review/import workflow for §3.3, not browser capture |
| Hinh_3 | S2 + S5 composite; different selected assets illustrate navigation through common asset identity, not shared geographic placement |
| Hinh_5_current | Controlled GeoPDF context, CRS and scale, only approved SPILLWAY reference symbol annotated; §4.1 |
| Hinh_6_current | S1 + S7 + S5 clean composite for §4.2 |

Copies named `S1.png`–`S7.png` and named Hinh composites are in `docs/paper_img`, with a mapping and checksum manifest. Current Hình 5 becomes final Hình 4 and current Hình 6 becomes final Hình 5 only when all manuscript cross-references are updated together. §5 refers back to Hình 2/3/current 5/current 6 and Tables 2/3; no extra Discussion screenshots.

### Controlled Table 2 and functional Table 3

Run `python3 scripts/export_paper_ui_counts.py` from repo root with the retained private snapshot and reviewed package. It reads files only and writes `results/paper/table_paper_2_counts.csv` and `.md`; it never connects to or writes the DB. Rehash the package after exports. Current counts: 4 targets, 4 researcher-reviewed identities, 0 verified canonical geometries, 1 reference location (separate), 3 technical records at L2, 0 assets with verified condition, 0 verified O&M events, 17 controlled sources, 12 expected-file sources, 5 distinct SHA-256 documents with IMPORT file-retention review, 1 selected 3D target, 1 representative verified link. Document retention review does not establish validated technical content. CSV definitions preserve each denominator.

For main-paper Table 3, select Registry/Detail, GIS selection, document preview, 3D load/select/deep link, O&M timeline and per-object highlight limitation from existing `table_t4_functional_validation.csv`; retain all F01–F21 in the package. This stage's targeted smoke is not a rerun or promotion of that historical matrix.

### Verification and unchanged research boundary

Ten targeted tests pass; modified frontend lint and production build/typecheck pass. Browser inspection covered Registry, GIS popup/panel, two-column detail, technical, document, O&M and representative 3D. Current document/3D tab error logs were empty after navigating through the configured API origin. Responsive stacking is implemented in CSS; no claim of a full device matrix. Native details were inspected for accessible/copyable canonical identifiers.

DB rows and retained media hashes before/after match exactly (`c32988b9918e65471eecf6bdbd96360d76f06478898d865c59450bc6806b8dd8`). All 46 controlled hashes and both provenance/location sidecar hashes match the previous snapshot. Package manifest contains 43 file hashes. Four canonical geometries remain NULL; SPILLWAY is reference only, INTAKE unresolved, DAM/MGMT have no location. Technical L2, zero verified O&M, LOCAL representative mapping, source authority, F02/F05 and NOT_READY/not frozen are unchanged. Private evidence records detailed checks and reproduction scripts.


## PAPER-DATA-ENRICH-RECAPTURE

Reused the supplied bounded pre-research; no broad Drive search or full archive OCR. Checks A–D and exact locators are retained in private `evidence/PAPER-DATA-ENRICH-RECAPTURE/decision_queue.md`.

- A: approved dictionary only contains the three historical wall keys. Monitoring count/period/0.50 m offset stay reference/review-pending; no MAIM extension or technical import. Monitoring-equipment operation does not establish DAM condition.
- B: workbook YEAR_ONLY entries lack exact completed-event dates; indexed XL1/XL5 findings concern design adjustment, contract/minutes dates or blank day/month. No qualified completed O&M event identified in the bounded review; no archive-wide absence claim.
- C: B01B/model review identifies a representative MGMT roof but does not establish name equivalence with sail building, operating complex or branch-office entrance. Mapping remains unresolved for those activity candidates; INTAKE ambiguity unchanged; no components created.
- D: exact DAM input-summary document RS-DOC-017 and hash match the existing DB document; no duplicate. Source map and workbook have no matching imported Document row and no direct supporting-document linkage contract in the existing API, which derives assets' documents via technical/O&M sources. Their relevance is retained, but no fake technical/event row or new schema was introduced to force links. Supporting-link candidates remain pending workflow support.

No qualified batch, so compiler/dry-run/apply/retry was not applicable. DB/media snapshot before and after is identical; all 46 controlled hashes and both sidecars unchanged. Document API links remain DAM=1, others=0. F02/F05 pending, dataset NOT_READY and not frozen.

UI: shared asset display wrapper and popup title use explicit left alignment; wrapped MGMT lines share the left edge across registry, detail, components and 3D. Browser computed style confirmed left. In paper panel only, actual reviewed technical records and meaningful document filenames come first; assets without technical evidence retain location-first layout. No empty states removed from full UI.

All S1–S7 were freshly captured, replacing working filenames after old images/hashes were archived under `evidence/PAPER-DATA-ENRICH-RECAPTURE/previous-docs` and `previous-paper`. Capture set `paper_data_enrich_recapture` records software commit, date, URL, DB/media and sidecar hashes. S1 selects DAM with L2 and document; S2 selects reference SPILLWAY; S3 shows L2 technical; S4 actual PDF; S5 MGMT LOCAL representative/left alignment; S6 true verified-empty O&M; S7 supplementary coverage. 3D uses preexisting allowed API origin 3000; other screenshots use temporary production preview 3100.

Hình 3 = S2 + S5. Hình 6 current = S1 + S3 + S5 because no qualified enrichment made coverage substantively richer. S7 remains supplementary/Table-2 support; S6 stays out of main figures. The S5 composite uses actual canvas, identity/LOCAL and asset-link excerpts, keeping empty O&M fields in full S5/S6. Hình 1/2 and source-map Hình 5 current are unchanged including hashes. Historic capture sets are preserved, not relabeled.

Table 2 exporter now accepts `--snapshot`; run `python3 scripts/export_paper_ui_counts.py --snapshot research/evaluation/evidence/PAPER-DATA-ENRICH-RECAPTURE/db-after.json`. This prevents silently exporting an older stage snapshot. Recomputed values and definitions below are unchanged. API-derived linked files differ from distinct retained documents.

| Metric | Before | After | Evidence / reason |
|---|---:|---:|---|
| Target assets | 4 | 4 | controlled RS asset count |
| Reviewed identities | 4 | 4 | researcher identity inclusion review / 4; not independent domain approval |
| Verified geometry | 0 | 0 | canonical RS geometry / 4; all null, no surveyed geometry |
| Reference locations | 1 | 1 | separate / 4; excluded from verified numerator |
| Technical records | 3 | 3 | RS records; level from bound reviewed provenance |
| L2 technical records | 3 | 3 | historical L2; no promotion |
| Verified current condition | 0 | 0 | assets with verified condition / 4 |
| Verified O&M events | 0 | 0 | verified condition/inspection/repair/maintenance records; not real-world activity count |
| Controlled sources | 17 | 17 | reviewed source inventory rows, including candidate/reference sources |
| Expected-file sources | 12 | 12 | file_expected=true; distinct from linked documents |
| Reviewed distinct documents | 5 | 5 | distinct SHA-256 among IMPORT file-retention reviews; not validated content |
| Selected 3D targets | 1 | 1 | approved requires_3d=true scope |
| Representative verified links | 1 | 1 | representative link records / 1 selected target; LOCAL, not full geometry |
| Asset-document API links | 1 | 1 | DAM 1; SPILLWAY/INTAKE/MGMT 0; source-derived, no direct link contract |

Targeted verification: 10 presentation/location tests, lint of modified TSX paths and production build/typecheck pass. Browser smoke covers selected DAM, SPILLWAY reference GIS, technical, actual PDF, MGMT 3D and alignment, O&M and coverage; no errors in inspected current tab logs. No full regression. Captions, figure-state, docs manifest and private 43-file package manifest updated.


## PAPER-EVIDENCE-ENRICH-2 — review checkpoint awaiting decisions

The private review packet is prepared: 14 downloaded PDF files with exact byte hashes; bounded visual review of the new manual, two top-level scans, office site plan/condition record and nine spillway scans; 41 candidates and a coherent seven-key optional SPILLWAY technical proposal. Maintenance prescriptions and generic failure examples remain reference content. Dated site observations are kept for genuine event/source review; office records require exact identity and effective-date review before any controlled MGMT/current-condition claim. No completed repair is inferred from design minutes or signatures.

Four logical source additions are proposals. Manual-first admission would change controlled-source/expected-file counts 17/12→18/13 if approved; neither denominator changes now. Source authority, mandatory MAIM, geometry, INTAKE identity and representative 3D scope remain unchanged. The user stated that professional review exists; the actual reviewer/role/date/key/source decisions are awaited. Private review_request.md now includes the seven proposed values/units/locators and response template.

`scripts/audit_evidence_enrichment.py` checks private bytes, locators, field-review binding, actual human role declaration, source admission/eligibility, exact dictionary label/unit, asset identity and event date/performed-activity boundaries before the existing compiler. It never approves data or writes DB/import batches. Four boundary tests and 48 existing compiler tests pass. Existing compiler produces NO_VERIFIED_CANDIDATES for the seven pending rows; dry-run/apply/retry awaits qualified approval.

After snapshot and API confirm the prior Table 2: 4 RS/4 researcher identities, geometry 0, reference 1, technical 3 L2, verified current condition/O&M 0, controlled sources 17/expected-file 12, distinct reviewed documents 5, selected 3D target/representative link 1/1. Source-derived document API associations remain DAM 1, other assets 0. All 46 active controlled hashes and provenance/location sidecars remain unchanged; no research original/approval signature is published.

No displayed data or UI changed, so S1–S7 and all composites/diagrams retain their exact bytes, existing capture set and UI commit 6c14892. Hình 6 stays S1+S3+S5; no old image is relabeled as a fresh capture. Figure state adds a separate data-review checkpoint, and the private package manifest now hashes 44 files. F02/F05 pending, NOT_READY and not frozen remain. No service was started.

Private packet: `research/evaluation/evidence/PAPER-EVIDENCE-ENRICH-2/review_request.md`, `evidence_candidate_review.csv`, proposed dictionary, field/source approval templates, source/evidence register, conflict notes and import gate report. Continue with the actual human field/source decisions, then compile→dry-run→apply→retry and recapture only affected figures.


## PAPER-EVIDENCE-ENRICH-2 — approval applied

The explicit user approval is recorded as nhuffan / RESEARCHER, not a fabricated domain-expert attestation. Seven optional SPILLWAY source-reported technical fields HYD-T01/T02/T08–T12 were admitted at L2, together with source RS-SRC-018 and retained document RS-DOC-041. Required MAIM and independent domain/methodology gates were not approved by this operation. Manual procedures remain reference material; no completed event or current condition was inferred. SP-I01–03 and MGMT identity/effective-date candidates remain pending their specific source/event contracts.

| Measure | Before | After |
|---|---:|---:|
| Technical L2 records | 3 | 10 |
| Controlled / expected-file sources | 17 / 12 | 18 / 13 |
| Distinct retained documents | 5 | 6 |
| API asset-document links | 1 | 2 |
| Verified condition / O&M | 0 / 0 | 0 / 0 |
| Canonical geometry / reference location | 0 / 1 | 0 / 1 |
| Selected 3D target / representative link | 1 / 1 | 1 / 1 |

Source remains UNKNOWN authority and UNVERIFIED independently of field-level L2 decisions. Dry-run → apply → retry completed: source/technical retry 8 UNCHANGED; document retry 1 UNCHANGED. Snapshot audit confirms only one source, seven technical records and one document were added; all prior rows and stored media hashes are unchanged. API and browser show seven SPILLWAY L2 records and one linked manual. Five review-boundary tests pass, including rejection of researcher-only approvals for required MAIM, L3 and events. No frontend/API schema changed; no new full build or full regression claimed.

S1/S2/S3/S4/S7 freshly captured at software d9a1c7c. S3 shows one expanded field/source excerpt, not all seven values. Public S4 is a metadata/toolbar crop; full page-1 preview stays private. S5/S6 and Hình 1/2/5 preserve old bytes/date/software. Hình 3 = new S2 + retained S5; Hình 6 = new S1 + new S3 + retained S5. Capture sets, captions, tables and hashes distinguish mixed capture lineage.

Methodology input checksums were refreshed without rebinding old approvals. Updated package remains NOT_READY / NOT_FROZEN; F02/F05 are pending. Previous package approval is stale and source-boundary/provenance methodology coverage needs reconciliation for added records. The private readiness-final report lists every gate. These imports do not establish research completeness or observed operational performance.

No task service was started; preexisting API, web and PostGIS remain running. Raw originals, approvals and candidate files remain private/ignored.

Methodology fingerprint: `fc806300b7fb12d5d3fccca193e2e203ed6c5caaf252b8a4b0dd7271a8525f90`. DB fingerprint: `49288aa558362c14f9c9238a92858ff05ed70e3d68a98a79bf9baf40ef7b4c72`.


## F02–F05–F15 image update 2026-10-15

Hình 3. Giao diện GIS hiển thị vị trí tham khảo của SPILLWAY (a) và mesh đại diện MGMT được chọn trong mô hình LOCAL (b). Hai panel thuộc hai asset khác nhau; hình không chứng minh đồng bộ tọa độ GIS–3D.

Hình 6. Prototype gồm thông tin SPILLWAY (a), thuộc tính L2 kèm nguồn manual (b), và mesh đại diện MGMT với highlight lựa chọn (c). Xác minh thuộc tính, thẩm quyền nguồn, vị trí và tình trạng vận hành là các trạng thái riêng.

S1/S2/S5 được chụp lại trên fdda470; S3/S4/S6/S7 giữ lineage cũ. F15 PASS theo kiểm thử Chrome thực; F02/F05 PENDING_EVIDENCE. Mẫu số: 4 asset, 0 canonical geometry, 2 reference locations, 10 L2, 18 sources/13 expected-file, 6 distinct documents/2 API links, 0 verified O&M, 1 selected 3D target/1 representative link. Ma trận 16 PASS, 2 FAIL, 3 N/A gồm các kết quả lịch sử được giữ lại; không phải chạy lại toàn bộ 21 tiêu chí. Word không chỉnh theo yêu cầu người dùng.
