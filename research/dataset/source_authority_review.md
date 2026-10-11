# Source authority, ownership and eligibility review

Use one private `reviewed/source_review.csv`, based on
[`source_review.template.csv`](source_review.template.csv), for the source-layer
review. Keep one row per controlled RS source, including missing, unidentified
and unused sources. The inventory remains the source/expected-file denominator;
this review does not delete inventory rows or rewrite imported records.

## Meaning of the review

Owner/custodian, named producer/issuer and authority are separate judgments.
Drive account ownership, institutional affiliation, filenames, folder names and
the project client do not by themselves prove document ownership or authority.
Record `UNKNOWN` with a reason when evidence is insufficient. A visible signature
or stamp is an observation, not independent authentication.

`authority_class` is `AUTHORITATIVE`, `SUPPORTING`, `REFERENCE`,
`UNKNOWN_AUTHORITY` or `NOT_ELIGIBLE`. Read it together with `authority_basis`,
the ten role-specific `eligible_*` fields and `eligibility_basis`. `YES` permits
the narrowly described use; it does not verify extracted facts, establish source
independence or authorize a new import. `NO` excludes the stated use;
`UNRESOLVED` requires further evidence. An exception for one physical file must
be explicit even when its logical group contains eligible material.

Coverage uses only supported target codes. An empty coverage list means
unresolved coverage, not absence of the assets. Separate document, issue,
revision, event and coverage dates; preserve content-supported year/month
precision (`YYYY` or `YYYY-MM`) instead of inventing a day. State which
representation each date describes. Upload timestamps and filename dates are
not event dates.

`digital_file_status` accepts `FILE_PRESENT`, `FILE_MISSING`,
`REPRESENTATION_ONLY`, `MULTIPLE_REPRESENTATIONS`, `NOT_EXPECTED`, `UNRESOLVED`.
Keep `file_expected` and `inventory_file_available` as unchanged inventory
values. Actual reviewed status may differ. A folder is not a physical file;
multiple archive leaves are not necessarily versions of one document.

`representation_relation` accepts `SAME_LOGICAL_SOURCE`,
`SAME_REVISION_DIFFERENT_REPRESENTATION`, `DIFFERENT_REVISION`,
`POSSIBLE_DUPLICATE`, `UNRESOLVED`. Retain exact evidence IDs, Drive IDs, page or
section locators and file hashes. Do not count exported or converted copies as
independent corroboration. Do not silently split/merge logical sources or remove
unrelated files from the audit trail.

## Private evidence and QA

Store evidence under `research/evaluation/evidence/SA/`, outside Git:

- `input_manifest.json` and `inputs/`: pre-review commit, reviewer/time,
  counts, hashes and copies of existing controlled inputs.
- `source_review_summary.json`: review-control counts and bounded coverage,
  including unresolved sources; these are not empirical performance metrics.
- `evidence_manifest.json`: retained file/text hashes and inspection coverage.
  Connector-extracted text hashes are not original binary file hashes.
- `provenance_checks.json`: five imported PDFs checked against the DB, evidence
  index, source IDs, original names, bytes, SHA-256 and page counts; original
  SKP → GLB hash/tool lineage; exact evidence for existing technical records.
- `potential_f02_f05_candidates.csv`: leads only, with follow-up requirements.
- `db-before.json`, `db-after.json`: complete data/media comparison; no automatic
  technical, geometry, O&M, model, link, condition or maturity promotion.
- `fingerprints.json`: old/new controlled hashes, reason, timestamp and a new
  SA package fingerprint. No prior approval is reused for this package.

Validate unique/exact inventory coverage, all source/evidence/asset references,
controlled values, reviewer/time, evidence for decisions and preservation of
missing expected sources. Inspect judgment quality separately: structural QA
cannot establish ownership, authenticity or research eligibility.

## Readiness and handoff

At completion of SA, this was an **auxiliary review artifact**, not a new formal input to the empirical
scope compiler. **MC supersedes that integration state:** see [methodology checkpoint review](../evaluation/methodology_checkpoint_review.md) for the formal inputs and current CLI. The remaining paragraph describes the SA-stage boundary. At that stage, compiler code, source inventory and case-study approvals remained
unchanged. In particular, do not fill inventory owner/authority fields with
`UNKNOWN` just to satisfy nonempty compiler checks. The SA package fingerprint
binds the new review independently; the unchanged legacy compiler fingerprint
does not attest to SA decisions. MC must explicitly resolve how approved
source decisions enter the protocol/compiler before freeze.

Run from `apps/api` with a fresh output directory:

```sh
uv run python -m scripts.prepare_empirical_scope \
  --base-scope ../../research/dataset/reviewed/base-scope.json \
  --targets ../../research/dataset/reviewed/target_assets.csv \
  --sources ../../research/dataset/reviewed/source_inventory.csv \
  --maim ../../research/dataset/reviewed/maim_requirements.csv \
  --review ../../research/dataset/reviewed/case_study_review.json \
  --acceptance ../../research/dataset/reviewed/functional_validation.csv \
  --applicability ../../research/dataset/reviewed/fv_applicability_review.csv \
  --output ../../research/dataset/reviewed/check-SA
```

Exit 2 with `NOT_READY` reports unmet gates; it is not permission to bypass
them. F02/F05 remain FAIL / PENDING_EVIDENCE, not N/A. Return to FV-R when
admissible geometry or dated O&M evidence is available. MC reviews remaining
methodology, scope/MAIM consistency and reviewer-independence limits. Do not
freeze DT-R1 until every required gate is satisfied.
