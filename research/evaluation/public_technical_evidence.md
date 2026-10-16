# Public technical evidence review

Private outputs are retained in `research/evaluation/evidence/PUBLIC-TECHNICAL/`: source register, technical candidate register, separate appendix, dedup/conflict report, INTAKE/MGMT identity sheets, review request, original W2 PDF/page renders, baseline/after snapshots and verification/readiness reports. No source or technical field is admitted by this stage.

The source-reported numeric candidate denominator is 19: 12 retained culvert-specific properties plus seven new historical DAM/SPILLWAY proposals. It excludes corroborating assertions, existing admitted gate count, mirror-only discoveries, reservoir context and proposed work. The admitted RS L2 denominator is independently read from API-bound provenance: 10 across four assets. Only the latter belongs in Table 4. Candidate keys are proposals, not dictionary entries.

W2 preserves original bytes and printed/zero-index page locators. Its historic gate count and intake discharges corroborate existing fields/candidates without increasing their counts. Main dam dimensions do not replace phase-II core-wall dimensions. Unknown datum and historic flood-design context remain explicit. W3 requires an authoritative original; W4/W5 original technical PDFs were not acquired. Existing drawings do not resolve MGMT identity. No numbered culvert mapping or child inventory is inferred.

## Reproduce paper tables

Run from repository root:

```sh
python3 scripts/export_asset_evidence_tables.py \
  --snapshot research/evaluation/evidence/PUBLIC-TECHNICAL/db-after.json \
  --api-readback research/evaluation/evidence/PUBLIC-TECHNICAL/api-readback.json \
  --controlled-dir research/evaluation/evidence/PUBLIC-TECHNICAL/inputs-before \
  --output research/evaluation/results/public-technical
```

Tables 1/4/6 are CSV and Markdown with input hashes. Acceptance dates remain historical; no new browser PASS. Before/after rows, media and protected files match. Review is still required for exact fields and source admission; only then may compiler/dry-run/apply/unchanged-retry/readback run. This stage does not alter Word, figures, source authority, geometry, maintenance or research freeze.
