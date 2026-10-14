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
