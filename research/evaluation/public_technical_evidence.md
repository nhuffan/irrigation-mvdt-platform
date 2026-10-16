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


## Explicit W2 approval applied

Vũ Viết Hải, self-declared RESEARCHER / TECHNICAL STAFF, approved W2 admission and PTE-01–07 as historical/design optional L2. Exact approval bindings and the agent-recorded receipt timestamp are retained in private `PUBLIC-TECHNICAL/approval-apply/`; no signature or independent/domain role is claimed. The earlier pending files remain immutable history.

Source RS-SRC-019 and seven technical records passed audit, compiler, rollback dry-run, apply and an eight-row UNCHANGED retry. Current L2 is17: DAM7/SPILLWAY10/INTAKE0/MGMT0; sources/expected-file19/14. Source authority/status remain UNKNOWN/UNVERIFIED. W2 PDF is retained privately with SHA-256; no new UI document attachment was imported, so distinct reviewed retained documents remain6 and asset-document edges2.

Current Tables1/4/6 are in `results/public-technical-approved/`; use approval-apply/db-after.json, api-readback.json and inputs-after with the same exporter command. The current candidate appendix has12 unresolved culvert fields; the source-reported cohort remains19, seven now admitted. Do not sum that cohort with the full admitted count17. Old exports and figures retain their original capture lineage; Word/figures were not updated.

Public-source compiler support accepts an HTTPS original URL plus SHA-256 and filename instead of a fake Drive ID. The evidence auditor checks original bytes and matching URL. Provenance preserves both fields. Browser verified DAM7/SPILLWAY10, their seven historical values and separate source authority/status; no geometry/O&M/3D acceptance rerun. Methodology remains NOT_READY with a new fingerprint and unchanged old approval bindings.
