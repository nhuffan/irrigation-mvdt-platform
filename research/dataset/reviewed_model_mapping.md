# Reviewed object mapping and 3D eligibility

Use the mapping and eligibility CSV templates beside this guide. Keep filled reviews, source files, visual evidence and batches in the ignored dataset directories. A mapping review and a decision about the empirical denominator are separate decisions.

## Exact object review

Check the retained GLB hash against the conversion manifest. Inspect active mesh names, scene position, bounds and isolated/highlighted renders. A tag name alone is insufficient. Flattened models may not retain a stable parent. An explicitly documented representative object may act as an asset access point when the viewer labels that limitation; it does not imply that every mesh of the asset is linked. Keep ambiguous and unavailable representations without links.

The single-link compiler checks byte hash, active-scene object identity, unique mesh names, all controlled target reviews, reviewer/timezone/evidence references and representative viewer semantics. It does not authenticate the reviewer or replace visual/domain review. The context JSON contains model_code, model_id, reservoir_id, glb_sha256, asset_ids (code→UUID), and representative_semantics. Populate identities from the audited existing records and preserve the context hash.

Run from `apps/api`:

```sh
uv run python -m scripts.prepare_reviewed_model_link \
  --mapping ../../research/dataset/reviewed/model_asset_mapping_review.csv \
  --context ../../research/dataset/batches/B03-M/context.json \
  --glb ../../research/dataset/evidence/B03/RS-MODEL-DT-001.glb \
  --output ../../research/dataset/batches/B03-M/new-link-review
```

A fresh output directory is mandatory. NO_VERIFIED_MAPPING produces no import batch. READY_TO_IMPORT generates at most one VERIFIED link with a stable UUID derived from model UUID, asset UUID and object key. Changing bytes requires renewed inventory/review; no automatic remapping.

Use `scripts.import_research_data --batch <batch.json> --log <new-log.csv>` for dry-run. Compare DB snapshots to verify rollback, then repeat with `--apply` and a fresh log. Retry must return UNCHANGED. Confirm the actual stored GLB checksum, exact model/asset/object relation, source and placement status, absence of unintended links and unchanged unrelated tables. Compiler context alone is not proof of the current DB/storage state.

## Eligibility and fingerprints

Archive targets and scope before changes. Record previous/proposed requires_3d, representation, study role, evidence, reviewer, timezone, approval and rationale for each target. Do not reduce the denominator merely to improve mapping success. Keep all controlled assets in the overall study even when current 3D-source eligibility differs.

After approved eligibility decisions and verified link import, update only reviewed requires_3d values and the explicit model_asset_links UUID allowlist. Archive both base-scope and full input fingerprints: the latter includes targets and therefore detects denominator changes. Never reuse approval of an old fingerprint. Re-run prepare_empirical_scope; outstanding reviews and browser acceptance must still block freeze.

## Browser evidence and next stage

Use the intended reviewed dataset. Click the actual representative mesh, verify the correct Asset ID/panel and open its detail page; also click unlinked objects to detect false associations. Save screenshots and a review log. Automated picking tests and keyboard selection alone do not establish canvas picking.

Continue with Stage 5B-FV using the controlled functional_validation.csv: F01–F06 and F19, plus F12–F14, F16–F17 and F20–F21 when any target requires_3d. Respect the full matrix and its remaining gates; F15 remains a disclosed non-blocking limitation. Targeted B03-M browser evidence is not full acceptance. Source authority/ownership and methodological checkpoints remain separate gates before READY_TO_FREEZE and DT-R1.
