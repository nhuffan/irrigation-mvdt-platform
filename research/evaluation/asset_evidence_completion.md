# Asset evidence completion and reproducible paper tables

This workflow separates source extraction from approved data. A named culvert or building in a document is not automatically the existing INTAKE or MGMT target. Keep candidate registers outside Git under `evidence/ASSET-EVIDENCE-COMPLETION/`, with separate proposed-feature names, raw values/units, source URL/hash, page/table/drawing locator, temporal basis, mapping decision and blockers. Candidate field keys are proposals, not additions to the controlled dictionary.

The 2026-10-15 review retains four Asset IDs. Numbered culverts remain separate candidate groups. The unnamed management house, office, dining building and sail building remain distinct possible features. No child assets, technical records, source admissions, reference points, canonical geometry or O&M events were imported. The existing LOCAL MGMT object remains representative-only.

## Reproduce Tables 1, 4 and 6

From the repository root, with the private snapshot/API capture and frozen controlled inputs available:

```sh
python3 scripts/export_asset_evidence_tables.py \
  --snapshot research/evaluation/evidence/ASSET-EVIDENCE-COMPLETION/db-after.json \
  --api-readback research/evaluation/evidence/ASSET-EVIDENCE-COMPLETION/api-readback.json \
  --controlled-dir research/evaluation/evidence/ASSET-EVIDENCE-COMPLETION/inputs-before \
  --output research/evaluation/results/asset-evidence-completion
python3 -m unittest discover -s scripts -p test_asset_evidence_tables.py
```

The read-only capture scripts `snapshot.py` and `capture_api.py` are retained in that private evidence directory; run them from `apps/api` with `uv run python ../../research/evaluation/evidence/ASSET-EVIDENCE-COMPLETION/<script>`. Snapshot capture takes `before` or `after`. `capture_api.py` creates the baseline manifest and checks linked document bytes against their registered SHA-256; do not overwrite the archived baseline during a later review. Capture API readback between equal before/after snapshots, and archive the input CSVs and sidecars before any import.

- Table 1 is the dataset aggregate. Controlled sources are inventory rows; retained documents are unique IMPORT-reviewed SHA-256 values with matching stored bytes. These are not interchangeable with source authority or claim coverage.
- Table 4 is per controlled in-scope asset. `linked_controlled_sources` counts technical/O&M source IDs, following the asset-document API relationship; it does not include unrelated source inventory rows or infer links from a building name. Document records are edges and can overlap across assets; distinct SHA-256 is counted separately. 3D links have their own column. Canonical geometry presence alone does not establish surveyed accuracy.
- L2 is read from the API's bound reviewed provenance and checked against snapshot technical records. Missing candidate values are excluded. Current condition uses the API's latest VERIFIED rule. O&M counts records, not deduplicated real-world activities.
- Table 6 preserves all controlled functional rows, original check dates, evidence paths and reviewer scope. A partial later browser session or API test does not replace the controlled acceptance. Read alongside the stage's `browser_acceptance.json`.

Every export includes input hashes and database fingerprint. No manuscript is changed. Paper figures from earlier stages retain their own capture dates and hashes; do not relabel them as new captures.

## Import gates still required

INTAKE needs an explicit source-backed mapping from its existing UUID to a numbered culvert, followed by field/unit/source review. MGMT needs an exact named building and site-plan/drawing locator, then separate technical and model-object decisions. Public-source admission is also pending. A reference location requires approved identity/reference mapping; canonical GIS additionally needs CRS, accuracy and domain review. Historical O&M needs eligible exact physical evidence, complete event date, completed-event semantics and the role-scoped review required by the existing audit/compiler. A researcher acknowledgment of a site record is preserved but is not relabeled as a domain-expert approval.

Methodology readiness remains separate from successful software checks. Re-run `scripts.prepare_empirical_scope` with the unchanged methodology package; never copy old signatures to a changed fingerprint.
