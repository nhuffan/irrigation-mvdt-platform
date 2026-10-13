# Annual maintenance evidence and approval review

Register each workbook as a controlled candidate source and physical evidence item before extracting activities. Preserve the original bytes, Drive ID, MIME type, hash, filename, reporting coverage and bounded review range in private evidence. Do not infer issuer, ownership or completion from the filename or Drive account.

## Candidate review

Use `maintenance_2021_2025_review.template.csv` and `maintenance_asset_mapping_review.template.csv`. A year/activity cell is one candidate; preserve raw text, source cell and year-header cell. Do not turn a reporting-year column into an event date. Inspect section context and explicit asset identifiers; culverts 1/2, diversion works, multiple buildings and similarly named assets in another reservoir must stay ambiguous or outside scope until matched. ACCEPT_CANDIDATE is a review-queue decision, not VERIFIED mapping or event verification.

Keep statistical/planned/reference entries outside DB until source eligibility, exact asset mapping, completed-event semantics, temporal precision, locator and reviewer are all supported. List missing evidence for each candidate. Registering an additional expected-file source increases the denominator; never remove unavailable baseline sources to improve coverage. Record and seek researcher confirmation for the updated denominator.

## F05 and the import contract

Read the exact controlled F05 wording. “Descending O&M timeline” does not itself specify full-date precision or authorize year-level chronology. The existing application stores SQL dates and the reviewed O&M compiler requires YYYY-MM-DD. This is an implementation constraint, not a newly invented F05 requirement. A reporting year cannot be filled with January 1 or another assumed day. Without verified completed events, a date-precision change alone would still not qualify evidence.

For later reviewed O&M batch preparation, carry the review columns into candidate rows: `temporal_precision`, `completion_status`, `source_eligibility`, `mapping_verified`. When supplied, the compiler requires FULL_DATE, VERIFIED, VERIFIED_EVENT and true respectively, in addition to existing provenance/date checks. These optional columns preserve legacy replay; do not drop them to bypass review findings. The two review CSVs are not import batches. No conversion from ACCEPT_CANDIDATE to VERIFIED is automatic.

If qualified evidence becomes available, use the existing reviewed O&M compiler and dry-run/apply/retry UNCHANGED workflow, then verify DB/API and retest actual browser chronology. Otherwise preserve F05 FAIL/PENDING_EVIDENCE without N/A. F02 remains separate: maintenance lists do not establish geometry/CRS/positional accuracy.

## Approval binding

Eight researcher policy confirmations can be recorded as RESEARCHER_APPROVAL / EIGHT_RESEARCHER_POLICIES for the current fingerprint. They do not satisfy RESEARCHER_APPROVAL / METHODOLOGY_PACKAGE or DOMAIN_REVIEW / MAIM. Update only gates directly resolved by the statement; keep checkpoint definitions, as-of date, study boundary and expert decisions separate. AI cannot sign external roles.

Embed exact UTF-8 bytes for both review CSVs under `candidate_evidence_review.reviews` in the methodology manifest, with SHA-256. The package fingerprint includes this evidence and the compiler checks both entries for checksum integrity. The top-level approval entries remain excluded from their own fingerprint; full compiled evidence retains them. Recompute fingerprint after controlled updates, bind only approvals actually given, and rerun formal readiness into a new output directory. NOT_READY is a valid outcome and must not emit a freeze scope.

Keep completed review CSVs, declarations, workbook, snapshots and reports in ignored directories. Commit reusable code/tests/templates and stage output only. See [methodology closure review](methodology_closure_review.md) and [reviewed O&M loading](../dataset/reviewed_om_loading.md).
