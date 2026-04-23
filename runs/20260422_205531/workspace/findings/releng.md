## Evidence
- Deploy CHK-2417 at 14:01:12 UTC to checkout-service fleet; rolling completion 14:01:12 → 14:03:45 across all pods.
- Release manifest included three dependency bumps and one runtime bump.
- **user-session**: 2.0.4 → 2.1.0 — **MINOR version bump** (not patch as PR author claimed).
- **express**: 4.18.1 → 4.18.3 — patch-level (x.y.Z).
- **pg**: 8.11.3 → 8.11.5 — patch-level (x.y.Z).
- **Node runtime**: 18.17.1 → 18.18.2 — minor version in Node's convention (18.17 → 18.18).
- Release notes for these three libraries were NOT reviewed before deployment. Standard practice does not mandate review of patch-level changes, but minor versions require review.
- Rollback manually triggered at 14:35:07 UTC, completed 14:37:50. Reverted all four bumps. Recovery followed.

## Timeline (my view)
- 14:01:12 UTC — Deploy CHK-2417 begins rolling out (user-session 2.1.0, express 4.18.3, pg 8.11.5, Node 18.18.2).
- 14:03:45 UTC — Rolling deploy completes across all checkout-service pods.
- 14:35:07 UTC — Rollback manually triggered.
- 14:37:50 UTC — Rollback completes.

## Initial hypothesis
The user-session minor version bump (2.0.4 → 2.1.0) introduced a behavior change that affects session validity, token handling, or session state integrity. Because this library is directly in the authentication and session path for checkout flows, a behavioral regression would explain:
- Partial success rate (92% vs. 0%) — sessions valid for some users/patterns, invalid for others depending on session creation time, refresh timing, or cache state.
- Correlation with deploy completion at 14:03:45.
- Immediate recovery on rollback at 14:37:50.

The express and pg bumps are patch-level and less likely to carry behavioral changes, but cannot be ruled out without examining their release notes. The Node runtime bump (18.17.1 → 18.18.2) is a minor version and could interact with the user-session library changes.

## Gaps / questions for others
- **sre**: What error patterns do you observe in checkout-service logs during 14:03:45 → 14:35 UTC? Specifically: session invalidation errors, 401/403 spikes, token verification failures, or session state mismatches?
- **observability**: Does cache behavior (Redis session cache, token cache) show anomalies at 14:03 UTC that match the success rate drop at 14:02–14:05?
- **support**: Are customer reports clustering around session loss, re-authentication demands, or first-try failures with subsequent success?
