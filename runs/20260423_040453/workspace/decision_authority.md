# Decision Authority and Escalation — Checkout v2 Launch

## Authority Timeline

### Thursday 2026-04-25 (PM returns from Tuesday–Wednesday out-of-office)

**Decision maker: PM (with input from ops/eng leads)**

- PM reviews pre-mortem, engineer load test results, ops dashboard/runbook readiness
- Authority: Full go/no-go on Friday 16:00 UTC ship
- Escalation: If PM has concerns, loop in CTO/exec sponsor before end of day
- No-go outcome: Document blocker, delay ship to following Friday

### Friday 2026-04-26, 16:00 UTC (Ship time)

**Decision maker: PM (or delegated lead if PM unavailable)**

- Ship is go (decided Thursday) unless a critical last-minute blocker surfaces
- Ops primary verifies dashboards live, runbook accessible, alerts firing correctly
- Engineer primary validates feature flag system and canary metrics baseline
- Rollback prerequisite: Confirm staged rollback test passed and runbook validated

### Friday evening into weekend (16:00 Friday – 12:00 Monday)

**Authority chain: Ops primary → Engineer secondary → PM on-call**

- **Ops primary (me):** Owns moment-to-moment monitoring, escalation routing, on-call communication
- **Engineer secondary:** Owns technical diagnosis, runbook troubleshooting steps, load analysis
- **PM on-call (availability: best-effort, limited):** Final authority on ramp pauses and rollback decisions

**Escalation protocol:**
1. If error rate or latency on v2 > pre-defined threshold (see Thresholds section), ops pages engineer
2. If engineer confirms degradation is v2-specific (stratified metrics comparison), ops initiates escalation to PM
3. If PM unreachable within 15 minutes, ops can **pause the ramp** (do not proceed to next stage), but cannot **roll back** without PM approval
4. If system is losing money, data, or audit-log integrity, ops can roll back immediately and notifies PM/exec after (see Autonomous Rollback section)

### Monday 2026-04-27, 12:00 UTC (100% ramp)

**Authority chain: Same as Friday evening. PM leads decision on ramp progression.**

- Ramp controlled by PM with input from ops (metrics) and engineer (technical health)
- Ramp stages: 0% → 25% → 50% → 100% (gates at each stage)
- Go/no-go decision at each gate: PM + ops + engineer consensus
- If consensus is "pause," ramp halts and team reconvenes in 30 minutes
- If consensus is "roll back," execute coordinated rollback (see Rollback Procedure section)

### Monday 2026-04-27, end of day (Ramp conclusion)

**Authority: PM (with ops/eng signoff)**

- PM authorizes "ramp complete" and v2 is now permanent, OR authorizes rollback if issues persist
- Final stakeholder notification: exec sponsor, compliance, legal (if applicable)

---

## Escalation Contact List

**Immediate escalation for on-call (Friday–Monday):**
- PM (launch decision authority): [contact info to be filled by lead]
- CTO / tech exec sponsor (if go/no-go decision has technical or business risk): [contact info]

**Legal/compliance escalation (if triggered by specific failure modes):**
- Compliance officer (if audit log integrity is questioned): [contact info]
- Legal (if customer-facing data loss or duplicate billing): [contact info]
- Payments team lead (if payment processing is affected): [contact info]

**Trigger conditions for executive escalation:**
1. **Audit log integrity:** If rollback fails partway or duplicate transactions are detected, escalate to compliance + legal immediately (affects attestation)
2. **Data loss:** If a rollback attempt leaves data inconsistent or unrecoverable, escalate to exec sponsor + legal
3. **Customer-facing outage:** If v2 or rollback causes checkout to be down for >15 minutes, escalate to PM + exec + support lead
4. **Revenue impact:** If error rate hits >5% and ramp cannot be paused, escalate to PM + finance/exec

---

## Decision Script for Ops / Engineering (Friday evening – Monday)

**If v2 error rate or latency is degraded vs. baseline:**
1. Ops validates signal in stratified v2-only metrics (not blended). Engineer pulls Datadog and confirms. If confirmed:
2. Ops initiates escalation: "@PM — v2 showing [error rate / latency] degradation at [percentage] ramp. Recommend pause and investigation. What's your call?" (in dedicated #checkout-launch-ops Slack channel)
3. Wait for PM response (target: 15 minutes). If PM unreachable, ops pauses ramp: do not proceed to next stage.
4. If PM is reachable and says "pause," ops toggles feature flag to hold at current stage. Engineer investigates root cause (logs, metrics, Redis health).
5. After 30 minutes of investigation, team reconvenes. If root cause is clear and fixable (e.g., "Redis eviction — need connection pool circuit breaker"), engineer proposes fix timeline. If fix is <30 min, attempt it. If >30 min or unclear, ops escalates to PM: "Rollback?" If PM says yes, proceed to Autonomous Rollback section.

**If v2 encounters schema mismatch error (column not found, constraint violation):**
1. This indicates rollback is unsafe. Escalate immediately to engineer + PM + DBA: "Schema incompatibility detected on v1 code path against v2-migrated schema. Rollback may fail. Coordinating with DBA for mitigation."
2. Do NOT attempt flag flip until DBA confirms schema can be reverted or migration is reversible.
3. Escalate to exec + compliance: "Potential rollback blocker due to schema state. Assessing customer impact."

**If ops detects idempotency-key duplicates in audit log:**
1. This indicates transactions are being double-processed during flag transitions. Escalate immediately to engineer + compliance: "Duplicate transactions detected in audit log. Audit log integrity may be compromised."
2. Engineer reviews transaction ledger (v1 vs. v2 view) to quantify duplicates.
3. Ops escalates to PM + compliance + legal: "Duplicate transactions [count] detected. Considering rollback and audit-log remediation."
4. PM + legal decision on whether to roll back or patch and remediate.

**Autonomous rollback (no PM approval needed):**
- **Scenario 1:** System is actively losing money (>5% error rate persists >10 minutes despite ops pause attempt, or revenue tracking shows significant loss)
- **Scenario 2:** Redis or session store is completely unavailable (all new checkouts failing)
- **Scenario 3:** Checkout system is totally down (0% success rate for >5 minutes)
- **Action:** Ops toggles feature flag OFF immediately. Notifies PM/exec via Slack and phone: "Rolled back v2. [Reason]. Impact: [error count]. Investigating."

**Post-rollback procedure (after any rollback, autonomous or authorized):**
1. Ops confirms v1 checkout is operational (spot-check with test transaction).
2. Ops pages engineer + DBA: "Rollback complete. Assess schema state and audit log for errors."
3. DBA checks v1 transaction processing against v2-migrated schema; report any failures.
4. Engineer reviews logs for idempotency-key misses or duplicate transactions.
5. Ops notifies PM + compliance: "Rollback complete. [errors/duplicates found or none]. Assessing restart readiness."

---

## Pre-launch Readiness Checklist (Ops responsibility, validate by Thursday EOD)

- [ ] Feature flag control plane tested and failover runbook in place
- [ ] Redis failover alert configured and tested (page ops on replication lag > 5s or session errors > 0.5%)
- [ ] v2 dashboards live and stratified (v2-only, not blended) metrics visible
- [ ] v2 runbook complete with error codes, dependencies, rollback procedure
- [ ] Support escalation channel (#ops-escalation or equivalent) is active and ops is monitoring (15-min triage SLA)
- [ ] DBA confirmed rollback schema compatibility test passed (v1 can run against v2-migrated schema, or rollback migration is documented)
- [ ] PM on-call phone/Slack confirmed available Friday evening
- [ ] Ops + engineer on-call verified they have decision_authority.md and can reference it
- [ ] Support team briefed on coupon endpoint, session re-auth changes, and feedback loop protocol
- [ ] Load test of Redis and coupon endpoint completed; latency/capacity baseline documented

---

## Definitions

**Ramp pause:** Feature flag percentage stays at current level (e.g., 25%) for ≥30 minutes while investigation happens. Customers on the flag see v2; new customers see v1.

**Rollback:** Feature flag OFF (0%). All traffic routes v1. v2 is disabled.

**Autonomous rollback:** Ops rolls back without waiting for PM approval due to severe system failure (Scenario 1–3 above).

**Authorized rollback:** PM approves rollback, ops executes.

**Go/no-go decision:** PM decides whether to proceed to next ramp stage (0%→25%, 25%→50%, 50%→100%).

**Audit log integrity:** Transactions recorded in the compliance-required ledger must have unique idempotency keys and must not duplicate during flag transitions or rollback.
