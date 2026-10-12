# Stage 5B empirical protocol

Status: **NOT READY / NOT FROZEN**. The checked-in inventories are empty templates. No domain review, browser acceptance, participant session or empirical result is asserted. DEV fixtures cannot establish case-study validity.

## Evidence and review gates

Use `dataset/target_assets.csv`, `source_inventory.csv` and `maim_requirements.csv` as controlled inventories. Keep completed copies in `dataset/reviewed/`, with the original documents and signed review evidence in the research archive. CSV booleans must be `true` or `false`; source related asset codes are pipe-separated. Target category is the registered category code. Geometry types are Point, LineString, Polygon or NONE. Exclusions require a rationale; included target identities require VERIFIED inventory review, even when an asset is not yet registered in the application.

Declare required fields by category. A required technical row needs its attribute key and expected unit (blank means no unit); all required attributes must have verified, nonmissing values. Zero is a value. Per-asset N/A exceptions need a written rationale in the base scope and review; they cannot remove assets from the identification/GIS/condition denominator. 3D eligibility comes from each target's `requires_3d`, independently of category-wide requirements.

Complete the study boundary, inventory, MAIM, source authority, identity, geometry, DEV separation and checkpoints A–D in `case_study_review.template.json`. Every approval requires an evidence reference and the review requires a reviewer and timezone-aware timestamp. Legacy sources require ownership, an eligible source type, authority/verification metadata and explicit digital-file expectation. For a scope opted into `STAGE-5B-MC-v1`, the formal source review and role-specific claim policy replace the blanket ownership/authority nonempty check; unknowns require explicit human acknowledgment and do not become verified. A missing expected file remains in the denominator.

Fill the existing `functional_validation.csv` from actual browser/manual checks on the intended dataset. Core checks F01–F06 and F19 must PASS. When 3D targets are selected, F12–F14, F16–F17 and F20–F21 must also PASS. Other checks can be N/A only with rationale; all blocking rows need reviewer, date and evidence. F15 per-object highlight is a disclosed limitation, not a freeze blocker. Correct selection panel and Asset ID resolution still require acceptance. Automated backend tests do not replace browser evidence.

## Compile a reviewed scope

Run from `apps/api`. First fill the existing scope template with the reservoir IDs, as-of date and explicit record UUID allowlists. Preserve its global MAIM list for Stage 5A compatibility; Stage 5B uses compiled per-asset rules. Prepare the inventories and review in `research/dataset/reviewed/`.

```sh
uv run python -m scripts.prepare_empirical_scope \
  --base-scope ../../research/dataset/reviewed/base-scope.json \
  --targets ../../research/dataset/reviewed/target_assets.csv \
  --sources ../../research/dataset/reviewed/source_inventory.csv \
  --maim ../../research/dataset/reviewed/maim_requirements.csv \
  --review ../../research/dataset/reviewed/case_study_review.json \
  --acceptance ../../research/dataset/reviewed/functional_validation.csv \
  --output ../../research/dataset/reviewed/check-01
```

The first run reports `base_scope_sha256`. Review that exact scope, record its fingerprint in the review, resolve blockers and rerun to a **new** output directory. Exit 2 means NOT_READY and produces only readiness.json. READY_TO_FREEZE also produces scope.json. This checks declared evidence consistency; it does not authenticate reviewers or verify the truth of their evidence. Changes to record allowlists, date, N/A or conflict decisions require renewed review. Embedded input hashes preserve the reviewed inventories; freeze/evaluation revalidate the compiled bundle.

Use the existing transactional import dry-run/apply workflow and archive import logs. Freeze with `scripts.freeze_research_dataset --scope <compiled scope.json> --output <new frozen directory>`, then evaluate with `scripts.evaluate_research_dataset --snapshot <snapshot.json> --output <new results directory>`. Do not use the legacy scope template directly for Stage 5B. Mark version.json frozen only after real acceptance, freeze and archival. A proposed DT-R1 label in a template is not a published dataset.

## MC methodology closure

The current MC workflow uses formal checksummed source, boundary, MAIM, reviewer, claim and readiness-gate inputs. See [methodology checkpoint review](methodology_checkpoint_review.md) for the complete CLI including `--methodology`, approval fingerprinting and compatibility policy. Once the reviewed base declares `methodology_protocol: STAGE-5B-MC-v1`, the legacy command above intentionally returns NOT_READY without that input. Do not remove the opt-in or reuse older approval to bypass MC.

## Metric specification STAGE-5B-v1

| Measure | Rule |
|---|---|
| Identification | Verified registered identities / approved target assets, including unregistered targets. |
| GIS | Valid stored geometry matching approved type / all target assets. This measures representation, not survey accuracy. |
| Technical | Assets with every required verified attribute and exact unit / targets eligible for technical requirements. |
| Current condition | Latest VERIFIED condition exists / all target assets; legacy asset condition is not substituted. |
| Inspection / maintenance | Targets with non-rejected records / targets requiring that MAIM field, excluding reviewed N/A. |
| Repair | Raw scoped record count is descriptive, not a quality score; optional eligible-target coverage is separate. |
| Documents | Expected-file sources remain the denominator even when files are absent; retained bytes must pass integrity checks. |
| 3D | Selected targets with reviewed VERIFIED mapping, known non-rejected source/model, documented placement and accessible unambiguous GLB object / selected targets. |
| MAIM | Required fields satisfied / applicable fields per asset; missing targets remain visible. |

Empty denominators produce null. Record verification and provenance remain inspectable. Conflict reviews must identify the exact conflicting record IDs with reviewer, evidence and rationale; unresolved/unreviewed values are retained. Optional `conflict_reviews` in the base scope accepts asset_code, attribute_key, record_ids, status (RESOLVED/UNRESOLVED/RETAIN_BOTH), reviewer, rationale and evidence_reference. Resolution does not delete raw values.

Exports include current_conditions.csv, geometry_review.csv, technical_requirements.csv and conflict_review_summary.csv alongside existing coverage/completeness/integrity tables. Legacy snapshots retain STAGE-5A-v1 calculations; do not pool results across metric specifications.

## Empirical sessions and paper evidence

Predeclare the answer key, task wording/version, targets, success criteria, timeout and workflow order. Collect actual BASELINE and MVDT sessions, timestamped in a declared timezone. Observation duration must match start/end within one second. Pair only the same dataset, task version, cohort, participant and task. Failed attempts stay in success-rate denominators; time reduction requires both attempts successful and baseline greater than zero. Do not infer missing task versions or timestamps when migrating old CSVs.

Use DOMAIN_STAFF and RESEARCH_TEAM participant groups. Research-team timings are benchmarks, not domain-staff validation. Keep consent and identities outside Git; the profile template uses pseudonymous IDs. Questionnaire Q1–Q8 is custom, not SUS. Preserve missing/N/A answers and report each item's actual n, including n=0. Do not combine cohorts to imply a larger domain sample.

Complete geometry review, qualitative coding and the results outline from evidence. Capture screenshots only from the frozen case study and link each table/figure to its dataset, metric specification and evidence archive. Report mapping/highlight limitations, missing sources, convenience sampling and small sample size explicitly. No claim of retrieval improvement, usability or research validation is warranted before those observations exist.

MC-R adds opt-in role-scoped approval and closure evidence; see [methodology closure review](methodology_closure_review.md). The current case study requires separate researcher package and domain MAIM approvals; AI consistency review does not satisfy either.
