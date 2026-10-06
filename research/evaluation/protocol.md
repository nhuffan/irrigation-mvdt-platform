# Evaluation protocol — draft for domain review

## Status and evidence boundary

The Stage 1–4 platform exists. This Stage 5 implementation supplies measurement tools and protocols; it does not establish an evaluated case study. Real inventory, source evidence, participants, baseline observations and browser acceptance remain pending. Do not report software seed fixtures or unit-test values as research findings.

Authoritative inputs: approved Phase 1 target inventory/MAIM, scoped database records, retained source files, actual observed sessions. Grain: one asset per asset metric; one technical/O&M record per traceability metric; one source per document coverage; one model-object mapping per mapping verification; one participant × task × workflow × dataset version per retrieval observation.

## Functional acceptance first

Use `functional_validation.csv`. Every manual item starts NOT_TESTED. Record PASS/FAIL, reviewer, timestamp, dataset version, expected Asset ID and evidence filename. Automated API/GLB tests do not prove visual rendering. Browser is unavailable in the current automation session.

For each media type actually in scope, test preview and download, missing-file state, unsupported file safety and Range. Test Cesium load, rotate, zoom, camera reset, pick, clear, deep link and unlinked object. The current viewer exposes selection in its side panel; per-object visual highlight has not been implemented/accepted and must not be marked PASS. Verify all three cross-module journeys from the supplied guideline. Capture screenshots without sensitive identifiers to `screenshots/` and add references to the matrix. Mark inapplicable types N/A with rationale, never PASS.

Compare GIS geometry against the approved spatial source/CRS, not merely successful rendering. Record positional tolerance before checking. Functional software correctness does not establish surveyed accuracy.

## Metric specification

| Metric | Numerator | Denominator / interpretation |
|---|---|---|
| Asset identification | Included assets with data_status VERIFIED | Verified Phase 1 target list, including targets not registered in DB |
| GIS mapping | Verified assets with valid non-null geometry | Included verified assets; validity is not positional accuracy |
| Technical coverage | Verified assets with ≥1 VERIFIED, non-null/nonblank value | Included verified assets; numeric zero is available |
| Condition coverage | Verified assets with ≥1 VERIFIED condition record | Included verified assets; missing never becomes Good |
| Inspection / repair / maintenance coverage | Verified assets with ≥1 scoped history record | Included verified assets; any verification state, explicitly presence-only |
| Source traceability | Scoped technical/O&M records linked to an included source | All scoped technical/O&M records, not expanded joins |
| Verified-source records | Source-linked records whose source is VERIFIED | All source-linked technical/O&M records |
| Verified record ratio | VERIFIED scoped technical/O&M records | All scoped technical/O&M records |
| Document coverage | Expected digital-file sources with ≥1 accessible frozen file | Explicit expected-source list |
| Document integrity | Documents with retained bytes matching recorded SHA-256 | All scoped document metadata; missing/unknown hashes do not count as matches |
| 3D coverage | Verified selected assets with a non-REJECTED link resolving to an unambiguous mesh node | Explicit 3D target list; link verification is reported separately |
| Mapping verification | VERIFIED links | All scoped research links |
| Technical conflict rate | Asset/key groups with >1 distinct nonmissing value/unit tuple | Asset/key groups with ≥1 known value |
| Source date known | Sources with source_date | Included sources; this is not a judgement of currentness |

Completeness reports per-target applicable MAIM field presence and mean/median/min/max. Identity/category/spatial/source are presence checks; technical/condition require verified records; histories are presence-only. N/A exceptions remove a field only with a written scope rationale. Candidate conflicts retain all record IDs; unit conversions and temporal revisions require expert adjudication. Missing fields and conflict flags are not automatically data errors. No inferred conflict resolution is exported.

Coverage summaries must show numerator, denominator and null reason. Scope has to be approved before running/reporting metrics. No enterprise scalability claim follows from two demonstration reservoirs. No maturity upgrade is performed.

## Retrieval study

Use a within-participant paired design if practical. Recruit irrigation engineers/operators/maintenance staff/managers with roles documented using pseudonyms. Set eligibility, recruitment method, sample size rationale and consent requirements with the research supervisor before recruitment. Do not send invitations automatically.

Provide identical information availability and a frozen version for both workflows. Document the actual folder/PDF/Excel/drawing workflow. Counterbalance order (half baseline first, half MVDT first) and use equivalent task/asset variants to reduce memorization; preserve an assignment ledger. Give equal training, a practice task outside the scored set, and a predefined timeout. Record environment/device/network, trial order, interruptions and assistance. Do not substitute API latency for human retrieval time.

Start timing when the task is revealed; stop when the participant submits an answer. Score against a source-backed answer key prepared by a domain reviewer. For failure/timeout, record actual elapsed time and success=0. Do not encode failures as zero seconds. Store evidence references, step count, wrong documents and confidence. Preserve raw observations.

Analyze matched participant/task/version pairs. Time reduction is computed only for pairs with both tasks successful and positive baseline time. Report all-attempt success rate separately and identify excluded/unmatched pairs; successful-only time comparisons have selection bias. Small samples support descriptive results, not statistical/causal improvement claims.

## Usability and qualitative feedback

Use the custom 8-item questionnaire after tasks; it is not SUS. Blank/NA answers remain missing. Report n per question, mean, median, range and sample SD only when n≥2. Do not aggregate dissimilar constructs into a validated scale. Preserve comments verbatim in a protected file, then code themes with reviewer and evidence references; no invented quotes or automated claim of saturation.

## Reproduction and limitations

Run frozen-dataset evaluation and participant export separately. Cross-reference dataset version and evidence manifest. Report source selection, missingness, unresolved conflicts, date limitations, sample/recruitment bias, training/order effects, hardware, lack of realtime data and prototype deployment limits. An evaluated study requires completed actual observations; code tests alone do not close these limitations.
