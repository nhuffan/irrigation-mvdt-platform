# Functional browser acceptance

Use the controlled `research/evaluation/functional_validation.csv` template and private reviewed copy. Preserve check IDs and function wording. Record actual browser observations, reviewer identity, timestamp, dataset version, expected asset UUID, evidence paths and limitations. AI-operated checks must not be described as human/domain approval.

Run the production build against the intended reviewed data. Snapshot DB rows, storage hashes, input files, frontend BUILD_ID and backend commit before testing. Keep DEV records out of empirical claims. Exercise real navigation, preview, camera, canvas picking, clear selection and deep links; automated tests and HTTP probes are separate evidence. A timeout or missing artifact is not PASS. Empty histories do not demonstrate chronology; missing geometry does not demonstrate spatial accuracy.

Keep evidence under ignored `research/evaluation/evidence/<run>/` and completed results under ignored `research/dataset/reviewed/`. Preserve baseline inputs. F01–F06/F19 and eligible 3D F12–F14/F16–F17/F20–F21 must PASS; F15 remains a documented nonblocking limitation when highlighting is unavailable. Other N/A rows need dataset-specific rationale. Follow the controlled matrix where prose numbering differs.

After tests, compare DB/storage/protected inputs, recompute the full input fingerprint and run `scripts.prepare_empirical_scope` into a new readiness directory. Acceptance does not approve source authority, change scope, upgrade maturity or authorize freeze. Record results and open blockers in STAGE_OUTPUTS.md, then stop only services started by the task.
