# MGMT identity and component evaluation scope

MGMT remains unresolved between a physical building and a managed complex. Nine prior candidate/context rows are retained separately from eight proposed-repair/BOQ rows. RAP2020 PDF13/printed11 corroborates an unnamed management house, not an exact office/sail/dining/duty-building or GLB identity. Tender technical bytes remain unavailable. No new source, field or O&M admission is claimed.

The private `base-scope.json` now contains `component_scope` (COMPONENT-SCOPE-v1): explicit child code/UUID, primary-parent code/UUID and technical record IDs, plus existing inventory/technical evidence references. The compiler binds this structure into its fingerprint and validates source references against primary plus declared component codes. Primary target inventory, MAIM and record allowlists remain unchanged. Actual DB identity/parent and exact child technical allowlists are checked by the exporter. Configuration is not a new human approval.

From repository root, reproduce the private tables:

```sh
python3 scripts/export_asset_evidence_tables.py \
  --snapshot research/evaluation/evidence/MGMT-IDENTITY-SCOPE/db-after.json \
  --api-readback research/evaluation/evidence/MGMT-IDENTITY-SCOPE/api-readback-all.json \
  --controlled-dir research/evaluation/evidence/MGMT-IDENTITY-SCOPE/inputs-after \
  --base-scope research/evaluation/evidence/MGMT-IDENTITY-SCOPE/inputs-after/base-scope.json \
  --output research/evaluation/results/mgmt-identity-component-scope
```

Table1 reports primary/component/all-tree asset and direct-L2 totals. Legacy aggregate rows retain the primary denominator. Table4 includes seven direct rows and explicitly named L2 totals; overlapping file/source totals are blank. Table6 retains historical status/date/evidence and annotates that component expansion has not been browser recertified. The manifest hashes all inputs including component scope. Omitting `--base-scope` retains the original primary-only contract.

Private evidence includes identity matrix, candidate/repair appendices, conflicts, pending identity decision, original RAP/hash/render, before/after snapshots, API captures, frozen inputs, verification and fresh readiness. No DB writes or importer retry are needed because no new fields qualify. Methodology remains NOT_READY/NOT_FROZEN; F02/F05 pending; historical F15 unchanged. Source/data approval is distinct from source-authority or domain-methodology approval.


## Subsequent parent decision

The user resolved MGMT as the parent management/operation complex and authorized creation of children when supported by drawings. Original03A p5 separately labels OFFICE, SAIL and DINING footprints; these three drawing-defined children are now registered. This is inventory identity, not surveyed geometry, present condition or a specific3D-object match. The spillway-duty building remains pending original evidence. Parent and all three building children retain zero L2; no field/source approval is inferred from the inventory decision.

Current reporting uses4primary+6components=10tree assets;17primary+18component=35L2. The private MGMT-PARENT-DECISION package and results/mgmt-parent-decision supersede the earlier unresolved-parent report while preserving it as history. Use the same export command with those paths and api-readback-all.json. Existing category/MAIM remain unchanged; parent scope is clarified through canonical name, description and controlled decision. No child L2 is rolled up to the parent.
