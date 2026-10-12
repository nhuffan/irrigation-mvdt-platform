# Methodology checkpoints and case-study readiness

MC uses **option A: formal compiler inputs**, under `STAGE-5B-MC-v1`. This
implements the review mechanism; it does not approve the study. The current
case-study outcome is **NOT_READY**. The user reports no separate methodology,
MAIM or independent-review confirmation. F02/F05 remain pending evidence;
F09 retains its prior download evidence and F15 remains nonblocking.

## Formal inputs and approval identity

Set `methodology_protocol: STAGE-5B-MC-v1` in the reviewed base scope. This
changes its fingerprint and makes `--methodology` mandatory. Keep a private
`methodology_review.json` based on the [template](../dataset/methodology_review.template.json).
Its `files` map names seven exact UTF-8 CSV inputs with paths relative to the
manifest and SHA-256 hashes:

| Input | Readiness role |
|---|---|
| `source_review.csv` | One source-layer review per controlled source; owner and issuer remain separate. |
| `source_boundary_review.csv` | Every evidence-index representation plus unlocated logical sources; exclusions remain in the audit. |
| `reviewer_independence_review.csv` | AI/human/domain/custodian/independent provenance, achieved level and limitations. |
| `readiness_gates.csv` | Required gates, actual state, evidence and explicit resolution path. |
| `maim_review.csv` | Per-target review of every existing MAIM rule and 3D eligibility, without implicit denominator changes. |
| `evidence_index.csv` | Controlled source-to-physical-evidence relationships. |
| `claim_sources.csv` | Exactly one provenance review per scoped technical/O&M/document/model/link UUID. |

The loader verifies actual file bytes. The compiled scope embeds those bytes
and revalidates checksums, tables, gates and approval offline during freeze and
evaluation. No later filesystem CSV is silently substituted. CSV changes require
new file hashes, a new package fingerprint and renewed approval.

The package fingerprint is canonical SHA-256 of the protocol, compiler context
(dataset, base fingerprint, record allowlists, targets, sources, MAIM, case-study
review, acceptance and applicability) and the methodology bundle excluding its
own `approval` object. This avoids circular signing. Complete all other reviewed
decisions first; use the compiler's `methodology_package_sha256` for final
approval. Approval must declare a human/domain/custodian reviewer, timezone-aware
time, evidence reference, the exact package hash, acknowledgment of unknown
ownership and acknowledgment of reviewer limitations. An AI declaration cannot
satisfy this gate. Software checks declarations, not reviewer identity or truth;
the signed/external evidence still needs human assurance.

## Role-specific source policy

MC replaces the legacy blanket nonempty `source_owner`/`authority_level` check
with source review and claim-level eligibility. It does **not** fill unknowns or
promote authority. Existing case-study approval and eligible-source-type checks
remain required.

- Technical, condition, inspection, repair and maintenance claims require the
  matching `eligible_* = YES` and `AUTHORITATIVE` or `SUPPORTING` authority.
- Documents and 3D may also use `REFERENCE`, for the explicitly limited
  retained-document/LOCAL-model purpose; this does not certify engineering facts.
- Every scoped claim requires an indexed evidence ID belonging to the source,
  an `IN_SCOPE` representation, supported target coverage, a precise locator
  and reviewer/time. `UNKNOWN_AUTHORITY`, `NOT_ELIGIBLE`, excluded, unresolved
  or duplicate representations cannot support a scoped claim.
- Unused, missing or reference-only sources remain in the inventory. Unknown
  owner/issuer is permitted as a reviewed limitation with human acknowledgment;
  it is never treated as confirmed ownership or primary authority.

The unrelated academic-risk submission representation identified in SA is
`OUT_OF_SCOPE_REPRESENTATION`. Its history stays in the index. The logical
submission group remains, with its relevant author-response documents limited
to reference use. No source split or denominator reduction is needed for that
exclusion. Other document pairs are not certified identical revisions simply
because their titles match; heterogeneous report/spreadsheet groups retain
their exact field-level locators. Unlocated representations remain UNRESOLVED
and need explicit boundary governance before closure.

## MAIM, functionality and reviewer limits

The per-asset MC review preserves the existing MAIM CSV. `effective_required`
must agree with that CSV, or with `requires_3d` for 3D. `PENDING_EVIDENCE`
describes missing evidence without weakening a requirement. Technical remains
optional pending a domain-approved field list: three historical attributes of
one wall component do not establish mandatory attributes for every category.
Do not invent additional keys or units to close completeness.

Geometry remains pending for all four assets. Hydraulic condition, inspection
and maintenance requirements remain required in MAIM; management-building
requirements remain as previously declared. Zero O&M records are retained as
missing data. Whether and how those findings support the research design needs
methodology approval; F05 remains an independent required chronology gate.
Per-asset documents remain optional in MAIM while the **11 expected-file
sources** remain the document denominator. Only MGMT requires 3D under the
existing explicit user approval; other assets stay in the overall study.

All F01–F21 are included in the gate inventory and must match the acceptance
matrix. F15 alone is nonblocking. N/A acceptance remains subject to the existing
compiler rules; F02/F05 require a separately approved, current applicability
review to be exempted. MC does not grant that exemption. Browser empty-state
success and automated tests do not establish geometry accuracy or chronology.

L0 is extraction, L1 source checking, L2 semantic checking and L3 independent/
domain cross-verification. The three retained technical records achieve L2,
not L3. Conversion, browser checks and workflow audit use NOT_APPLICABLE where
the field-level ladder does not apply. A user's identity/scope declaration is
recorded as human review within its stated limits; it is not automatically
domain, custodial or independent review. No such independent confirmation is
currently supplied. MC requires human governance of these limitations, not a
fabricated expert review.

An additional scope issue remains explicit: earlier spillway/intake identity
references use SKP while later 3D mapping cannot identify those structures
unambiguously. Retain the user-approved identities; request suitable identity
evidence/clarification. Missing 3D does not mean the real assets do not exist.

## Required gates and compatibility

The compiler requires `MC_SCOPE`, `MC_BOUNDARY`, `MC_SOURCE_POLICY`, `MC_MAIM`,
`MC_REVIEWER`, `MC_APPROVAL`, `MC_INTEGRITY`, `MC_PROVENANCE`, `MC_HASHES` and the
complete functional matrix. Required nonfunctional gates must PASS; required
FAIL/PENDING/UNRESOLVED states block a scope. Every unresolved gate has an owner
action expressed in `resolution_path`. Case-study checkpoints A–D and all
existing approvals remain separate; a blank or stale case-study review cannot
be approved by an AI audit or by a gate row alone.

Legacy inputs without the MC opt-in retain their existing behavior for historic
reproducibility. This is not permission to remove the opt-in from the current
case study. The flag participates in the base-scope fingerprint; removing it
invalidates reviewed scope context. MC adds governance, not a new metric
formula: metric specification remains `STAGE-5B-v1`.

Run from `apps/api`, using a new output directory each time:

```sh
uv run python -m scripts.prepare_empirical_scope \
  --base-scope ../../research/dataset/reviewed/base-scope.json \
  --targets ../../research/dataset/reviewed/target_assets.csv \
  --sources ../../research/dataset/reviewed/source_inventory.csv \
  --maim ../../research/dataset/reviewed/maim_requirements.csv \
  --review ../../research/dataset/reviewed/case_study_review.json \
  --acceptance ../../research/dataset/reviewed/functional_validation.csv \
  --applicability ../../research/dataset/reviewed/fv_applicability_review.csv \
  --methodology ../../research/dataset/reviewed/methodology_review.json \
  --output ../../research/dataset/reviewed/check-MC
```

Exit 2 means NOT_READY and creates only readiness.json. READY_TO_FREEZE requires
all existing and MC gates, current human approval, coherent scope/MAIM, valid
claim sources and verified input integrity. Do not create DT-R1 before that.

Private results live under `research/evaluation/evidence/MC/`: input archive,
dataset integrity, document denominator, approval reuse, candidate follow-up
triage, hashes and `readiness_report.md`. Prior identity, 3D and L2 decisions
may remain evidence for their unchanged narrow roles; they do not sign this new
MC package. A promising source candidate is a FV-R review lead only. When new
F02/F05 evidence arrives, review/import/retest through FV-R and rerun MC; only
then consider the FR freeze/reproducibility stage.

## MC-R role-scoped extension

For current closure work use [methodology closure review](methodology_closure_review.md). Its declared ROLE_SCOPED-v1 policy supersedes the legacy single-reviewer approval for that package; legacy replay remains supported.
