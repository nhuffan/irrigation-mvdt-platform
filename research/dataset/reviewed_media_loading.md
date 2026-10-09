# Reviewed documents and 3D loading

Keep source files, filled reviews, conversion manifests and audit logs in ignored `evidence/`, `reviewed/` and `batches/`. Header-only templates beside this guide describe the review records. Importing a file does not approve its engineering claims or source authority.

## Documents

Run from `apps/api`, after reviewing the manifest and retaining original evidence filenames:

```sh
uv run python -m scripts.import_reviewed_documents \
  --manifest ../../research/dataset/reviewed/document_review.csv \
  --evidence ../../research/dataset/reviewed/evidence_index.csv \
  --evidence-root ../../research/dataset/evidence \
  --output ../../research/dataset/batches/B03/document/new-dry-run
```

Inspect the dry-run report, then repeat with a fresh output directory and `--apply`. Never overwrite an audit directory. Retry the identical manifest with another output directory to verify UNCHANGED records. The importer validates source/evidence identity, physical bytes, SHA-256, MIME, PDF page count and duplicate representations. Stable UUIDs derive from source UUID and document code. Existing mismatched identities or metadata fail instead of overwriting.

Dry-run rolls back DB writes and uses temporary storage. Apply commits one DB transaction; content-addressed files can remain as unreferenced bytes if that transaction fails. Check the FAILED marker and verify committed DB/API records before interpreting logs as success.

## Models

Retain the original SKP, converter version/archive hash, invocation, output hash, GLB object inventory and render inspection in a private conversion manifest. B03 used Blender 4.4.0 and SketchUp importer 0.24 after explicit user authorization. The imported GLB was re-imported and rendered for inspection. Flattened hierarchy and generated names do not establish asset identity.

Use the existing research-data importer for a reviewed models batch, following its dry-run/apply/retry workflow. Keep LOCAL coordinates and null geographic placement when survey alignment is unavailable. The web viewer supports LOCAL preview without inventing an Earth position. Verify metadata, content hash, Range responses, reservoir listing and asset-link responses after import.

Do not add model_asset_links until object-to-asset mappings have been reviewed. For B03 the four candidate mappings remain AMBIGUOUS/UNVERIFIED, deferred by the user. No new asset is created from a model object. The reference GLB is about 137 MiB and has not been optimized for constrained devices.

Update only imported document/model/link IDs in the private scope allowlist; preserve missing expected documents in the denominator. Re-run empirical readiness. A rendered model and successful API responses do not constitute full functional acceptance or authorize a dataset freeze.
