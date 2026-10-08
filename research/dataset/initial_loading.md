# Initial candidate data loading (B01A)

B01A loads only category taxonomy and candidate source metadata. Asset identities, geometry, hierarchy, technical/O&M data, documents and models require later review. Presence of RS codes does not mean VERIFIED evidence or READY_TO_FREEZE.

The three supplied drafts are preserved byte-for-byte in the private `reviewed/` directory. `batches/B01A/` contains the generated batch, reserved UUID map, input hashes, dry-run/applied logs, before counts and verification report. These files and original evidence are ignored by Git; retain a private backup. No original source documents were supplied or imported. Inventory file availability is an unverified claim, not confirmation of a file in storage.

From `apps/api`, prepare a new batch directory once:

```sh
uv run python -m scripts.prepare_initial_research_batch \
  --targets ../../research/dataset/reviewed/target_assets.csv \
  --sources ../../research/dataset/reviewed/source_inventory.csv \
  --maim ../../research/dataset/reviewed/maim_requirements.csv \
  --reservoir-id <existing-reservoir-uuid> \
  --reviewed-by '<structural import reviewer; domain review pending>' \
  --output ../../research/dataset/batches/B01A
```

The converter accepts UNVERIFIED drafts only and reserves asset UUIDs without inserting assets. It preserves complete dates; partial dates/ranges remain NULL with original text in notes. It does not infer file names from titles, owner, authority, technical values or geometry. The reviewer field records structural conversion review only, never domain approval.

Reuse the saved batch and UUIDs for retries; an existing output directory is rejected. Before applying, run `scripts.import_research_data` without `--apply`, review the log and verify rollback. Then use the same batch with `--apply` and a new log path. Differing existing records are rejected; corrections require a reviewed procedure. Never regenerate IDs to bypass a conflict.

Current controlled review and functional checks remain pending; the compiled-scope check correctly returns NOT_READY. Source metadata can be retrieved by source UUID through `/api/v1/data-sources/{id}`. The reservoir asset endpoint continues to show existing DEV assets because B01A deliberately adds no research assets. No new UI or research-verified label is introduced.

Next: review original sources and target identity/inclusion (especially management building), then prepare B01B using the reserved asset IDs. Review geometry, MAIM technical keys/units, source ownership and domain evidence before approving any empirical gate. DT-R1 remains NOT_FROZEN.
