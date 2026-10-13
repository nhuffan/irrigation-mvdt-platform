# B02 technical and O&M review/import

`prepare_reviewed_om_batch` compiles explicit reviewed candidates offline. It never reads source values automatically, writes the database, promotes source status or adds research-scope membership. AI-extracted values remain REVIEW_PENDING until field-level review. Prior source/package approval is not approval of every future extraction.

## Candidate representation

Templates live in `research/evaluation/templates/`. Keep populated CSVs and original evidence private under `dataset/reviewed/` and `dataset/evidence/`. Archive original candidates before migrating the B01B schema: map UNVERIFIED to REVIEW_PENDING explicitly, not to VERIFIED.

Use candidate_id, asset_code, record_type, source_code, evidence_id, source_locator, candidate_date, candidate_field, candidate_label, candidate_value, candidate_unit, candidate_status, reviewer, reviewed_at and notes. Additional explicit columns resolve ambiguities:

- `candidate_value_type`: number/text for technical values. The compiler never guesses types. Numeric zero is valid; missing/NaN/Infinity are not.
- `record_payload`: JSON object of actual type-specific DB fields for an event. IDs, dates and verification fields cannot be injected into this object.
- `event_basis`: explanation that the source documents an event, rather than a monitoring/model observation. Required for dated O&M.
- `literal_value_reason`: rationale only when a placeholder-like literal text is itself a meaningful fact.

Only selected-type VERIFIED candidates are importable. EXTRACTED, REVIEW_PENDING, REJECTED and NOT_APPLICABLE remain out. MONITORING, MODEL_OUTPUT and REFERENCE never become O&M automatically. Every selected record requires a reviewed physical evidence file, matching source/asset links, approved target inclusion, reviewer, timezone-aware timestamp and an exact locator (PDF:p12:table-2, DRAWING:sheet-03:note-7, XLSX:Sheet1!B12:D16, or DOCX:section "Name"). Source verification remains separate and may be UNVERIFIED; REJECTED sources are blocked.

Technical fields must match category-specific dictionary key, label and exact unit. Normalization requires a reviewed update to candidate and dictionary; do not silently convert units. Initial dictionary entries derived from candidate evidence are proposals until the corresponding field review. Do not make them MAIM-required merely because a value is readable.

Event payloads use the existing schemas. Conditions need condition_status; repairs need repair_description; maintenance needs description; inspections need summary or observation. Every event needs a real full YYYY-MM-DD candidate_date; year/month/range must not become an invented date. Unknown inspector/responsible_unit remain absent. Repair proposals/design adjustments are not proof of completed repairs.

## Compile

Run from `apps/api`:

```sh
uv run python -m scripts.prepare_reviewed_om_batch \
  --candidates ../../research/dataset/reviewed/b02_candidate_records.csv \
  --attributes ../../research/dataset/reviewed/technical_attribute_dictionary.csv \
  --evidence ../../research/dataset/reviewed/evidence_index.csv \
  --sources ../../research/dataset/reviewed/source_inventory.csv \
  --targets ../../research/dataset/reviewed/target_assets.csv \
  --id-map ../../research/dataset/batches/B01A/id_map.csv \
  --batch-type technical \
  --reviewed-by '<field reviewer>' \
  --output ../../research/dataset/batches/B02A
```

Other types: repairs, conditions, inspections, maintenance. Success writes B02-<type>.json, id_map.csv, provenance.csv, review_manifest.json, input_sha256.json and verification_report.json. Use separate condition/inspection outputs. No reviewed candidates means exit 2, NO_VERIFIED_CANDIDATES and reports only; invalid selected candidates block the whole batch. No empty import batch is fabricated. Existing output directories are rejected.

UUIDs are deterministic UUIDv5 of reserved asset UUID + record type + stable candidate ID, then persisted. Keep candidate IDs stable; changing a value reuses the record UUID so the importer rejects silent overwrite. Distinct conflicting candidates keep distinct records; conflict groups are reported for review, not resolved automatically. Review manifest/hash and provenance bind record → candidate → evidence → logical source → Drive file + exact locator. Archive these beside the source bytes; DB source_id alone does not contain the page locator.

## Apply and verify

Dry-run `scripts.import_research_data --batch <B02-type.json> --log <new-dry-run.csv>`; confirm rollback, record IDs and batch hash. Apply that exact batch with `--apply --log <new-applied.csv>`. Preserve logs and verify retry UNCHANGED. Differing existing records require reviewed correction, never a new ID to bypass a conflict.

Verify Technical/O&M/current-condition/timeline API for each RS asset. Technical values are not timeline events; a missing VERIFIED condition must remain null. Check reservoir maturity/source states unchanged. Compiler reports imported_count=0 because it does not apply data; preserve a separate post-apply verification report with actual counts/logs.

Only after reviewed imports are stable, add their exact UUIDs intentionally to the private base-scope record allowlists. Do not select all RS rows. Keep MAIM/geometry/browser review separate. Stage 5B stays NOT_READY until the later review gates pass; no DT-R1 freeze during B02.

Current extraction is an initial bounded pass, not a complete review of the archive. Missing O&M in the database is not proof no O&M exists in unexamined files.

## Annual statistical workbook candidates

Follow [maintenance evidence review](../evaluation/maintenance_evidence_review.md) before preparing annual-workbook O&M. Preserve explicit time/completion/source/mapping review columns; candidate acceptance alone does not establish a verified event.
