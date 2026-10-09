# B02-R field review and B02-I handoff

The private `reviewed/B02-review.md` holds the source-specific review, not the project README. Header-only templates alongside this file define the verification log, crosscheck matrix and conflict review; working CSVs, PDFs and generated batches remain ignored and must be backed up with the research evidence archive.

## Decisions and provenance

Use L0 for extraction, L1 for a confirmed source transcription, L2 for confirmed meaning, asset linkage and unit/date basis, and L3 only for an independent matching source or explicit domain-expert confirmation. A matching drawing and report may share an origin: numerical agreement alone does not establish L3.

Only VERIFIED decisions with four PASS checks (source, semantic, asset, unit/date), L2/L3, named reviewer and timezone-aware timestamp are eligible. Record AI inspection, user declaration, domain review and automated checks separately. Historical component values must be labelled as such; do not silently substitute whole-asset dimensions, present-day measurements, survey datum or model parameters.

`final_decision` belongs in the verification log. The current compiler candidate schema does not have KEEP_AS_REFERENCE: preserve original CSV/payload in an input archive, retain the candidate as REFERENCE with NOT_APPLICABLE import status and record KEEP_AS_REFERENCE in notes/log. This does not remove a research asset or create a MAIM N/A exception. Log the original and final record types when reclassifying an event.

An empty conflict CSV means no conflicting candidate values identified within documented coverage, not proof that the archive is conflict-free. Record unread pages, illegible scans, repeated sheets and filename/titleblock date discrepancies in the private coverage report. Do not infer event dates from filenames.

## Import handoff

B02-R is an offline review. The current eligible B02A output is at `batches/B02-R/B02A/B02-technical.json`, with persisted UUIDs, provenance and input hashes. `batches/B02-R/handoff_verification.json` binds review-file hashes and the exact batch bytes. This is an audit binding; the existing compiler does not independently authenticate reviewers or engineering truth.

Before B02-I apply, compare those hashes with the current files, inspect all review decisions, verify references in the live DB, then run from `apps/api`:

```sh
uv run python -m scripts.import_research_data --batch ../../research/dataset/batches/B02-R/B02A/B02-technical.json --log ../../research/dataset/batches/B02-R/B02A/dry-run.csv
```

Review the dry-run log and rollback result. Only then apply that same batch with a separate applied log and `--apply`. Verify DB/API values, asset/source links, absence of unintended O&M events, latest-VERIFIED condition behaviour and idempotent retry. Do not overwrite an existing differing record. Update explicit record allowlists only after successful apply. No batch should be created for an empty category.

B02-R does not approve source authority, complete archive review, browser acceptance, freeze or empirical effectiveness. Keep Stage 5B NOT_READY until those gates are actually satisfied.

## B02-I execution status

The existing three-row B02A batch has now been applied. Private `batches/B02-I/verification_report.json` records the reviewed dry-run/rollback, first apply, unchanged retry, DB/API snapshots, protected input hashes and scope fingerprint change. The technical allowlist contains exactly those persisted batch UUIDs; other allowlists and MAIM are unchanged. The earlier B02-R handoff remains historical evidence, including its pre-import base-scope hash; the intentional later scope change is recorded separately. Do not overwrite old audit logs or regenerate the reviewed batch to repeat this stage. Further corrections require a new reviewed cycle. Readiness remains NOT_READY, and no freeze or browser acceptance has been performed.
