# Functional acceptance remediation

Classify evidence gaps separately from software defects. A browser download passes only after a real click completes and the downloaded filename, byte count and SHA-256 match the retained document. HTTP Range and preview are separate checks. Download links use the same-origin attachment endpoint; previews retain their Blob URL.

## Controlled applicability

Copy `research/dataset/fv_applicability_review.template.csv` into the ignored reviewed folder. F02/F05 start as KEEP_FAIL or PENDING while evidence remains unresolved. Do not declare archive-wide absence from a bounded review. A CRS-labelled overview map may still lack asset geometry/accuracy; a dated contract/design adjustment is not a dated operational event.

Only F02 and F05 can receive `APPROVED_NA`. The explicit decision must preserve the original requirement, explain why it is inapplicable to authentic evidence, name the reviewer, include a timezone timestamp, evidence review scope, rationale, protocol effect and decision reference. Set `evidence_found=false`, `proposed_applicability=N/A`, and record an affected browser retest with `requires_retest=true`, `retest_status=PASS`, and its evidence. This retest verifies truthful absence/display after an approved applicability change; it does not claim accuracy or chronological ordering.

Bind the decision to dataset version, `base_scope_sha256` and `scope_input_sha256`. The latter is `research_common.digest` of `{base_scope_sha256, targets, sources, requirements}` using the same parsed input rows as the compiler. Changed targets, sources, MAIM or allowlists invalidate old exemptions. Include all applicability rows in the full-input fingerprint. Reviewer identity and engineering truth still require assurance outside syntax validation; AI must not impersonate human approval.

Run the existing `scripts.prepare_empirical_scope` command with the additional option:

```text
--applicability ../../research/dataset/reviewed/fv_applicability_review.csv
```

Use a fresh output directory. No option means the original strict gates remain. Pending/KEEP_FAIL rows cannot exempt anything; malformed, stale, duplicate or unrelated approved exemptions block readiness. Compiled scopes retain reviews and validate them again before use. Acceptance exemptions never change MAIM denominators, geometry, O&M records, authority or maturity.

## Handoff

Store source review findings and exact page coverage privately. Preserve previous matrix and fingerprints. Only update affected acceptance rows. Keep F15 disclosed as a nonblocking limitation. Stage SA starts after blocking FV items are resolved or explicitly governed; a code change alone does not close FV-R or authorize freeze.
