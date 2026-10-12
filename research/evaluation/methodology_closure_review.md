# MC-R methodology closure review

MC-R separates AI consistency review from role-scoped approvals. It does not authenticate a signer's real-world identity. Keep empirical files and signed evidence in the ignored `research/dataset/reviewed/` and `research/evaluation/evidence/MC-R/` directories.

## Controlled inputs and approvals

Retain `methodology_protocol: STAGE-5B-MC-v1` in the base scope and add `methodology_approval_policy: ROLE_SCOPED-v1`. Declare matching `approval_policy` in the methodology manifest. The base fingerprint includes this policy; deleting or mismatching it blocks compilation. Legacy MC packages without this extension still replay under their original semantics; do not downgrade a current package to bypass its declared policy.

Keep the seven existing `files` entries. Add `closure_files` entries for `mc_r_gate_resolution`, `researcher_methodology_confirmation`, `maim_closure_review`, and `ai_consistency_review`; each has `path` and SHA-256 of exact UTF-8 bytes. The loader embeds these as `closure_inputs`. Their content and checksums participate in the package fingerprint and offline replay. The compiler validates integrity, not the truth of AI judgments or arbitrary CSV statements; human review must inspect the content.

Use `approval: {"entries": []}` until approvals exist. Each entry follows `../dataset/methodology_approval.template.json`. Required type/scope/role combinations:

| Type | Scope | Role |
| --- | --- | --- |
| RESEARCHER_APPROVAL | METHODOLOGY_PACKAGE | RESEARCHER |
| DOMAIN_REVIEW | MAIM | DOMAIN_EXPERT |

CUSTODIAN_CONFIRMATION requires CUSTODIAN; INDEPENDENT_REVIEW requires INDEPENDENT_REVIEWER. These are not mandatory under the current bounded-use/L2 policy and cannot replace either required approval. Each supplied entry must be unique by type/scope and include an APPROVED decision, current package fingerprint, name, timezone-aware timestamp, evidence, and boolean limitations acknowledgment. Never label AI as one of these roles. A new protocol is needed if additional approval scopes become mandatory.

The top-level approval object is excluded from its own package fingerprint to avoid circular signing; the compiled-scope input hash includes it. Populate all controlled decisions first, compile to obtain the fingerprint, then record genuine approvals against that fingerprint. Changing review evidence invalidates prior approvals. Case-study checks, as-of date, acceptance and individual gates must independently pass; a package signature does not bypass them.

## Closure outputs

Assign every unresolved required gate exactly one primary owner and blocker group. Retain the raw count alongside unique group count; grouping is not resolution. AI may resolve consistency only. Preserve F02/F05 as FAIL/PENDING_EVIDENCE, F15 nonblocking, L2 technical records and missing GIS/O&M. Review every MAIM row without weakening requirements because data is unavailable.

Use the four empty CSV templates in `research/dataset/`. Write `gate_reconciliation.json`, `methodology_closure_report.md`, and before/after fingerprint audit. Prepare external requests only where required; do not send them without user authorization. Record prior narrow approvals as such, never as approval of a new package.

Rerun the same full command in [methodology checkpoint review](methodology_checkpoint_review.md), using the updated manifest and a fresh output directory such as `reviewed/check-MC-R`. NOT_READY / exit 2 is expected while evidence or approval is missing. Verify no scope/freeze was emitted, compare DB/media and protected-input snapshots, then update STAGE_OUTPUTS.md. Current private results are not exported to Git.
