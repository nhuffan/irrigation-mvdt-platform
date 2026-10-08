# Research dataset

Status: **NOT FROZEN**. No approved case-study inventory or participant observations have been supplied. `version.json` deliberately has no published dataset version. Database seed counts in `../evaluation/readiness_audit.json` describe software readiness only.

## Research membership and scope

Use `RS-` codes for reviewed research assets, sources, categories, documents and models. The prefix is a segregation convention, **not proof of real-world verification**. Preserve original identifiers in source records and the reviewed inventory mapping. Existing reservoir UUIDs may be reused; reservoir maturity is not promoted by these scripts.

Copy `scope.template.json` to a private working file and fill it from the approved Phase 1 inventory. Record reviewer, inventory reference, as-of date, reservoir UUIDs, every target asset code, included source codes, and explicit UUID allowlists for technical/O&M/documents/models/mappings. Unregistered target assets stay in the identification denominator. Do not remove inconvenient missing assets. A new record is excluded until explicitly added to a new scope/version.

Document denominator: only sources expected to have a digital file. 3D denominator: only assets selected for representation. MAIM fields and per-asset N/A exceptions require domain review. Empty denominators produce null, not 0%. Repair is not a required MAIM field by default; add it only when appropriate. `as_of_date` is the reference date for the approved scope, not a claim that all sources are current.

## Import, freeze, evaluate

Run from `apps/api` with local database/environment configured:

```sh
uv run python -m scripts.import_research_data --batch ../../research/dataset/batches/B01.json --log ../../research/dataset/batches/B01-dry-run.csv
# After reviewing the batch and dry-run, apply exactly that batch:
uv run python -m scripts.import_research_data --batch ../../research/dataset/batches/B01.json --log ../../research/dataset/batches/B01-applied.csv --apply
uv run python -m scripts.freeze_research_dataset --scope ../../research/dataset/batches/DT-R1-scope.json --output ../../research/dataset/frozen/DT-R1
uv run python -m scripts.evaluate_research_dataset --snapshot ../../research/dataset/frozen/DT-R1/snapshot.json --output ../../research/evaluation/results/DT-R1
```

Import JSON follows `import.template.json`: a map of table labels to arrays of records with explicit UUIDs. Labels: `asset_categories`, `data_sources`, `assets`, `technical`, `conditions`, `inspections`, `repairs`, `maintenance`, `models`, `model_asset_links`. Within each group, order parents before children. Fields match the existing domain models; geometry accepts GeoJSON EPSG:4326. Supply asset `data_status` and every record's `verification_status` explicitly. No script upgrades verification. Referenced reservoirs must already exist. Import is transactional; dry-run rolls back, identical IDs/values are unchanged, differing existing records are rejected. Corrections need a separately reviewed migration/import procedure, not blind overwrite.

Import document files with the Stage 4 `scripts.import_documents` command using an RS- document code and reviewed source. This calculates SHA-256 and records provenance; preserve the command/batch reference in the import log. Register model metadata through the reviewed batch only after placing the approved self-contained GLB in configured storage with its recorded key. Storage copies and source files must be retained with import evidence.

Freeze uses a read-only REPEATABLE READ transaction, explicit record membership and same-reservoir checks. It copies accessible document/model bytes into content-addressed `files/` and records missing files explicitly. `snapshot.json` contains scope, data and SHA-256; evaluation verifies the JSON and retained file hashes without reading the live DB. Existing freeze/output directories are rejected. Hashes detect accidental changes; they do not authenticate a reviewer or make a filesystem immutable. Archive the bundle read-only with external version control/sign-off before citing it.

Batches, frozen source documents, participant observations, screenshots and generated result folders are gitignored. Back them up in an approved research evidence repository. Do not commit participant identities or proprietary source files. Update `version.json` only after actual reviewed freeze, including the snapshot SHA-256 and evidence archive reference.

For Stage 5B, use the [empirical review and metric protocol](../evaluation/stage5b_protocol.md) to compile the reviewed scope before freeze. The Stage 5A scope template alone does not enforce Stage 5B checkpoints.

For the initial unverified categories/source load, see [B01A workflow](initial_loading.md).

For reviewed asset identities and optional geometry, see [B01B workflow](reviewed_asset_loading.md).
