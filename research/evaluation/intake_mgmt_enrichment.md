# INTAKE / MGMT evidence and component inventory

The explicit user decision approves RS-DT-INTAKE as parent of RS-DT-INTAKE-C01/C02/C03, corresponding to culverts1/2/3 and East/West/Tan Hung canals. Existing `parent_asset_id` supports this without a migration. Component inventory and UUIDs are retained separately; the four primary targets and empirical record allowlists are unchanged. The UI registry may list all seven RS assets; this is not the paper's four-primary denominator.

Private `evidence/INTAKE-MGMT/` contains original SIWRR bytes/page47 render, source hashes, reviewed identity/geometry inputs, exact user decision, compiler outputs, rollback/apply/retry logs and before/after API/DB evidence. SIWRR October2010 printed47 (PDF index46) and W1 Table2.2 printed25/index24 agree on three culverts' n/B/H/Q. Eighteen candidate properties comprise twelve retained fields plus three canal names and three sill levels. Source admission and technical review remain pending; inventory approval does not admit them as L2. No fake Drive IDs are used for public sources.

MGMT keeps nine prior candidate/context rows and eight plan-only proposed-repair/BOQ rows separate. Original tender drawings/BOQ were not obtained. Office/sail/dining buildings remain distinct; the representative model does not establish identity. Internal scupper specifications are not railing evidence. Incidental main-dam height32m versus W2 historical28m, and office scupper58.6mm versus50.8mm, remain unresolved and do not overwrite admitted data.

## Reproduce primary tables

```sh
python3 scripts/export_asset_evidence_tables.py \
  --snapshot research/evaluation/evidence/INTAKE-MGMT/db-after.json \
  --api-readback research/evaluation/evidence/INTAKE-MGMT/api-readback-after.json \
  --controlled-dir research/evaluation/evidence/INTAKE-MGMT/inputs-after \
  --output research/evaluation/results/intake-mgmt
```

The private output directory contains Tables1/4/6 CSV+Markdown with input hashes, and component_appendix.csv/.md with its own input manifest. Primary API readback excludes components intentionally; component-api-readback.json checks all three child parent IDs, empty technical collections and null geometry. Do not add child candidate counts to primary admitted L2. No manuscript, figure or References changes.
