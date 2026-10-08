# B01B reviewed asset loading

`prepare_reviewed_asset_batch.py` is an offline compiler. It never writes the database, regenerates IDs, upgrades review states or overwrites a prior output directory. Use the reserved B01A UUID map. Default database asset status is REGISTERED, even when identity review is VERIFIED.

## Controlled inputs

Keep targets, identity review, geometry review, evidence index, logical source inventory and MAIM in the private `reviewed/` directory. Preserve the previous inputs before corrections. Source inventory describes logical sources; evidence index describes exact files/folders. Multiple formats of a report do not automatically count as independent sources.

Identity review columns: asset_code, candidate_name, canonical_name, category_code, in_scope, parent_asset_code, identity_status, primary_evidence, secondary_evidence, reviewer, reviewed_at, rationale. Each target requires a decision. Included targets require VERIFIED identity, matching name/category/parent and explicit true/false inclusion. Exclusion requires rationale. Review timestamps include timezone.

Evidence purpose is pipe-separated IDENTITY, GEOMETRY, TECHNICAL, REPAIR, MONITORING, REFERENCE, SOURCE_AUTHORITY or 3D. Review status is PENDING, REVIEWED, VERIFIED or REJECTED. REVIEWED records the declared document review, not source authority or complete asset verification. Primary identity evidence must include a reviewed physical file associated with that asset; a folder alone is insufficient. Enumerate leaf files in repair folders.

Geometry review columns follow the supplied guideline, with optional `geometry_geojson` added for an inline bare GeoJSON geometry. Blank means NULL and requires NOT_AVAILABLE, survey_grade=false and a rationale. Supplied geometry requires reviewed status, CRS/method/confidence/provenance, matching evidence/file ID, output EPSG:4326 and matching expected type. Shapely checks topology; coordinates must be finite 2D lon/lat, and polygon rings explicitly closed. This validates representation, not survey accuracy. No coordinates are inferred from document approval.

## Compile and import

From `apps/api`:

```sh
uv run python -m scripts.prepare_reviewed_asset_batch \
  --targets ../../research/dataset/reviewed/target_assets.csv \
  --identity-review ../../research/dataset/reviewed/asset_identity_review.csv \
  --geometry-review ../../research/dataset/reviewed/geometry_review.csv \
  --evidence ../../research/dataset/reviewed/evidence_index.csv \
  --id-map ../../research/dataset/batches/B01A/id_map.csv \
  --reservoir-id <existing-reservoir-uuid> \
  --reviewed-by '<domain reviewer>' \
  --output ../../research/dataset/batches/B01B
```

Success writes B01B-assets.json, input_sha256.json, review_manifest.json and verification_report.json. Parents are ordered before children; cycles/out-of-scope parents are rejected. Failure writes a NOT_READY report and hashes, no importable batch. Retry with corrected inputs in a new directory. Hashes bind declared review inputs, not reviewer authentication.

Run the existing `scripts.import_research_data` with `--batch <B01B-assets.json> --log <new-dry-run.csv>`. Review rollback and the hash-matching log before repeating with `--apply --log <new-applied.csv>`. Preserve batch/review hashes and all logs. The generic importer rejects silent changes to existing assets; later geometry corrections require a reviewed correction procedure.

Verify DB counts, asset detail and reservoir-list API, NULL or reviewed geometry, idempotency and unchanged reservoir maturity. API success is not browser acceptance or empirical validation.

## Current review basis and limits

The user confirmed review/approval of supplied Drive/local documents in this task. The private B01B-user-review.json preserves the statement and its context; identity/inclusion uses the supplied four-target inventory under that declaration. No independent authentication of domain review is claimed. Inspection coverage is recorded separately in evidence/B01B/inspection_coverage.json. The AI did not render the SKP or inspect every page in the Drive package.

B01B preserves missing geometry. MAIM remains the supplied initial requirements, without invented technical keys/units. The B02 candidate queue contains a reference transcription, not an imported O&M fact. Source-owner/authority gaps and unknown revision equivalence remain open. The updated logical source inventory is a controlled working file; it has not silently overwritten B01A source rows in the database. Those corrections need separate reviewed migration/import handling.

Batch files, source PDFs, user review declarations and CSV evidence are private/gitignored. Back them up separately from Git. Do not mark the overall empirical checkpoints, browser checks or DT-R1 freeze complete from B01B alone.
