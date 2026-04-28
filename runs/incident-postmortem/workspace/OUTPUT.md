# Incident Postmortem — Checkout Degradation, 2026-04-20

## Timeline (consolidated)

- 14:01:12 UTC — Deploy CHK-2417 begins rolling out to checkout-service fleet (user-session 2.0.4 → 2.1.0, express 4.18.1 → 4.18.3, pg 8.11.3 → 8.11.5, Node 18.17.1 → 18.18.2)
- 14:02:14 UTC — HTTP 401 spike begins on `/session/validate` endpoint (baseline ~3 req/min → ~310 req/min by 14:18)
- 14:02 UTC — Checkout success rate drops from 99.8% to 92.1%; Session Redis cache-hit-rate falls from 94.1% to 61.3%
- 14:03:45 UTC — Rolling deploy completes across all checkout-service pods
- 14:05:12 UTC — Scheduled primary DB failover initiates (routine weekly maintenance, pre-scheduled; not triggered by errors)
- 14:05:39 UTC — DB failover completes; session Redis cluster shows zero cascade effects, no evictions, health metrics stable
- 14:20 UTC — `/session/validate` error rate peaks at ~18%; errors continue at sustained elevated rate
- 14:35:07 UTC — Rollback manually triggered, reverting all four dependency/runtime bumps
- 14:37:50 UTC — Rollback completes
- 14:42 UTC — Checkout success rate recovers to 99.8%, `/session/validate` errors drop to baseline 0.2%, Session Redis cache-hit-rate recovers to 93.7%

## Root Cause (hypothesis)

The 14:01 deploy introduced **user-session 2.1.0** (minor version bump, mislabeled as patch-level by PR author), which modified session TTL handling. **Sessions now expire after ~2–3 minutes instead of the normal multi-hour lifetime.** When users log in, their session is valid briefly, then marked expired (`SES_EXP`) on the next `/session/validate` call (occurring within 2–5 minutes). Users must re-authenticate, but newly-issued sessions follow the same 2–3 minute expiry cycle. This forced users to re-login multiple times during checkout, resulting in 92% checkout failure rate and ~$180k revenue impact.

The session expiry pattern is precise (not random), indicating a hardcoded or miscalculated TTL constant in user-session 2.1.0. The library is directly on the session validation code path (`/session/validate` 401 errors, support tickets reporting "had to re-login 3 times," SRE logs showing session_id cycling valid → 401 → valid → 401 every 2–3 minutes). The 8% of checkouts that succeeded either completed before their first session expiry, or benefited from caching layers that served older session data.

**Evidence supporting this hypothesis:**
- **SRE logs:** Session IDs cycling valid → 401 (SES_EXP) → new session → 401 again, all within 2–3 minute windows. Spike begins 14:02:14, only 71 seconds after deploy completes.
- **Support tickets:** 38 of 47 tickets (81%) report identical pattern: "logged in fine... worked for a couple minutes then kicked me out again." Ticket #18431: "Got logged out mid-checkout THREE times."
- **Observability metrics:** `/session/validate` error rate 0.2% → 14.8% exactly correlates with deploy completion. Session Redis cache-hit-rate drops 33 percentage points but cluster infrastructure is healthy (no evictions, no memory pressure, no connection storms) — indicating application code changed session validation behavior, not infrastructure failure.
- **Releng evidence:** user-session 2.1.0 is documented as a MINOR version bump (behavior-change risk), not patch-level. Convergent evidence from all four domains points to TTL or session validation logic change.
- **Temporal causality:** Deploy at 14:01, errors at 14:02:14 (71-second lag for rolling deploy + pod startup). Rollback at 14:35 → recovery by 14:42 (5-minute lag for new pods to stabilize). No other infrastructure change correlates.

## Counter-evidence considered

**DB Failover (14:05:12–14:05:39):** Was this a contributing cause?
- **Ruled out.** The failover was pre-scheduled routine weekly maintenance (Monday 14:05 UTC slot), not alert-triggered by the 14:02 error spike.
- Session validation errors began at 14:02:14 UTC, 3 minutes BEFORE the failover initiated. If failover had triggered the errors, it would have started immediately, not waited 3 minutes.
- Session Redis cluster showed zero cascade effects: no evictions logged, memory and CPU stable, no network saturation during the failover window.
- Cache-hit-rate drop (94.1% → 61.3%) occurred primarily during 14:02–14:06 UTC, before the failover. The drop was already 20 percentage points down by the time failover started at 14:05.
- Recovery only occurred post-rollback (14:35–14:42), not post-failover (14:05–14:42). This definitively attributes the cache-hit-rate collapse to the deploy, not the failover.

**Remaining uncertainty:** The exact mechanism (hardcoded TTL constant vs. changed validation logic vs. cache key generation change) cannot be confirmed without direct access to user-session 2.1.0 release notes and source code diff. The evidence converges on session TTL modification, but the specific code change is unknown.

## Contributing factors

1. **Process failure — minor version bump incorrectly reviewed as patch-level.** The PR author labeled user-session 2.0.4 → 2.1.0 as "routine patch-level update," when it is a MINOR version bump that routinely carries behavior changes. Releng reviewed and approved without examining the actual changes. Standard practice does not mandate release notes review for patch-level bumps, but minor versions require review. This allowed a behavioral regression to reach production.

2. **No canary validation for dependency bumps.** The rolling deploy had no canary hold: the fleet was configured for uniform rollout, not 5% canary for 5 minutes. The first pod to receive user-session 2.1.0 was immediately broken. The bug manifested within 71 seconds of first pod completion and should have been detected within the first 2 minutes of the rolling deploy.

3. **No session TTL or session lifecycle testing in CI.** Automated tests likely verify "can I create a session" and "can I validate a session," but not "does the session TTL match expectations" or "does the session expire at the expected time." This behavioral regression passed CI.

4. **Insufficient logging in session service.** SRE application logs do not include session-layer cache hit/miss indicators, TTL values, or session state metadata. While observability correctly identified the cache-hit-rate drop via metrics, SRE could not trace the specific mechanism from logs alone.

## Remediation

- **releng (immediate, by 2026-04-23):** Retrieve user-session 2.1.0 release notes and source code diff from npm. Confirm whether TTL was hardcoded, validation logic changed, or cache key generation modified. Document exact change in postmortem appendix. Owner: release engineering lead.

- **releng (short-term, by 2026-04-29):** Implement mandatory code review for all minor (x.Y.z) and major (X.y.z) version bumps: reviewer must examine release notes and source diff, document risk assessment, approve or reject explicitly. No minor/major bump deploy without documented review. Owner: release engineering lead.

- **releng (short-term, by 2026-04-29):** Implement canary deployment for all dependency-bump and runtime-bump deploys: deploy to 5% of fleet, measure error rate for 5 minutes, require error rate to remain <0.5% above baseline, only then proceed to 100%. Owner: release engineering lead.

- **platform/SRE (short-term, by 2026-04-30):** Add integration tests to session service that verify session TTL behavior and session lifecycle (create session → validate immediately (expect OK) → wait T+expected_TTL → validate again (expect SES_EXP)). Add tests for all session creation patterns (new user, returning user, token refresh). Owner: platform/SRE engineering lead.

- **releng (medium-term, by 2026-05-06):** Audit all currently-deployed dependency versions in checkout service and related services against their upstream release notes. Identify any other minor or major bumps that were incorrectly treated as patch-level in recent reviews (last 30 days). Document findings and remediate any discovered regressions. Owner: release engineering lead.

## Unknowns

- **Exact mechanism in user-session 2.1.0:** Whether the session TTL was hardcoded to a shorter value, validation logic was rewritten, or cache key generation changed. Pending retrieval and review of 2.1.0 release notes and source diff from npm.
- **Why exactly 8% of checkouts succeeded:** Whether the 8% was due to users completing checkout within the first session-validity window, caching layers serving stale session data, or a third pattern. Application logs insufficient to determine; would require checkout flow tracing and cache-layer instrumentation.

---

**Incident declared RESOLVED at 14:42 UTC.** Rollback deployed, system recovered, remediation owners assigned.