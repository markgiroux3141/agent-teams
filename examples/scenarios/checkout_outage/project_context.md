# Incident context — Checkout degradation, 2026-04-20

**Incident:** Checkout success rate dropped from 99.8% to 92% between
14:02 and 14:42 UTC on Monday 2026-04-20. ~40 minutes. Recovery
correlated with the release engineer triggering a rollback at 14:35.

**Severity:** SEV-2. Revenue impact estimated ~$180k in lost/abandoned
transactions. Compliance team notified (audit-log continuity was not
affected).

**What we know going in:**
- Something changed around 14:00–14:02.
- Rolling back at 14:35 recovered the system by 14:42.
- The outage was NOT total — success rate dropped to 92%, not 0%.
  Users who succeeded did so on their first try. Users who failed did
  so with varying patterns.

**What we don't know:**
- The root cause. Multiple possible stories are live:
  1. Auth/session system malfunctioned.
  2. A scheduled DB failover at 14:05 caused side effects.
  3. The deploy at 14:01 was not as innocuous as its manifest claimed.
- Whether there's more than one cause compounding.
- Whether this will recur if we redeploy the rolled-back version.

**The postmortem's job:**
Converge on a root-cause hypothesis supported by cross-referenced
evidence from four domains (logs, metrics, deploys, customer reports),
list contributing factors, and assign remediation owners. The correct
answer is NOT in any single domain's findings — it requires a join.

**Team:** sre, observability, releng, support. IC is running the
postmortem.

**Output:** `OUTPUT.md` should contain timeline, root-cause hypothesis
with evidence + counter-evidence, contributing factors, remediation
owners, and unknowns.
