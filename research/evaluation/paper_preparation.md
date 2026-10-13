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

The remaining methodological/domain approvals are documented in the package closure report. An actual as-of boundary cannot be inferred from the screenshot date. The optional summary card was not added because existing sections already expose the relevant states and counts.
