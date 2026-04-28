# Ramp Metrics Plan — Checkout v2 Launch

## Overview

This plan addresses the critical gap flagged in pre-mortem: ramp metrics are currently aggregated and blinded to v2-specific degradation. Without stratified metrics, ops has no clear go/no-go signal for each ramp stage (0% → 25% → 50% → 100%), leading to delayed rollback decisions and extended user pain.

**Requirement:** Stratified (v1 vs v2 side-by-side) metrics dashboard must be live and tested in staging by Friday before ramp begins Monday. Automated alerts must be armed and tested Friday afternoon.

---

## Stratified Metrics Dashboard

### Location and Access
- **Platform:** Datadog (existing checkout monitoring)
- **Dashboard name:** `Checkout v2 Ramp — Metrics Comparison`
- **Audience:** ops-checkout (primary), engineer (secondary), PM (ramp decisions)
- **Accessibility:** Bookmarked in #ops-checkout Slack, linked in decision_authority.md and on-call runbook

### Dashboard Panels (v1 vs v2 side-by-side)

#### Panel 1: Conversion Rate
- **Metric:** Successful transactions / attempted transactions (% completed checkout)
- **Comparison:** v1 baseline (30-day average) vs. v2 current (during ramp)
- **Time range:** 1-hour rolling window, updated every 5 minutes
- **Visualization:** Line chart with two series (v1 dotted baseline, v2 solid live)
- **Threshold annotation:** Add red zone <95% of v1 baseline (e.g., if v1 is 72%, red zone is <68%)
- **Success criteria:** v2 stays ≥ 95% of v1 baseline at all ramp stages

#### Panel 2: Error Rate (all endpoints)
- **Metric:** 4xx + 5xx errors / total requests (%)
- **Comparison:** v1 baseline vs. v2 current
- **Time range:** 1-hour rolling, updated every 5 minutes
- **Visualization:** Line chart with threshold lines
- **Thresholds:** 
  - Green: v2 error rate ≤ v1 baseline + 0.5%
  - Yellow: v1 baseline + 0.5% to +1%
  - Red: > v1 baseline + 1%
- **Success criteria:** v2 error rate stays in green zone

#### Panel 3: Checkout Latency (p50, p95, p99)
- **Metric:** Response time from checkout API call to completion (milliseconds)
- **Comparison:** v1 vs v2, three lines per version (p50/p95/p99)
- **Time range:** 1-hour rolling, updated every 5 minutes
- **Visualization:** Multi-line chart, colors: v1 (gray), v2 (blue)
- **Thresholds:**
  - p50: v2 ≤ v1 + 50ms (v1 baseline ~200ms → v2 target ≤250ms)
  - p95: v2 ≤ v1 + 100ms (v1 baseline ~800ms → v2 target ≤900ms)
  - p99: v2 ≤ v1 + 150ms (v1 baseline ~1500ms → v2 target ≤1650ms)
- **Success criteria:** v2 latency stays within thresholds for all percentiles

#### Panel 4: Coupon Endpoint Success Rate
- **Metric:** `/v2/coupons/apply` successful responses / total requests (%)
- **Breakdown:** By coupon code format (if available) to catch edge cases
- **Time range:** 1-hour rolling, updated every 5 minutes
- **Visualization:** Single line with threshold zone
- **Thresholds:**
  - Green: > 98%
  - Yellow: 95% to 98%
  - Red: < 95%
- **Success criteria:** Coupon endpoint stays > 98% success rate throughout ramp

#### Panel 5: Coupon Endpoint Latency (p50, p95, p99)
- **Metric:** Response time for `/v2/coupons/apply` (milliseconds)
- **Percentiles:** p50, p95, p99
- **Time range:** 1-hour rolling, updated every 5 minutes
- **Visualization:** Three-line chart
- **Thresholds:**
  - p50: < 100ms (new endpoint, should be fast)
  - p95: < 300ms
  - p99: < 500ms
- **Success criteria:** Latencies stay within thresholds

#### Panel 6: Checkout Error Rate Breakdown (v2 only)
- **Metric:** 5xx / 4xx / timeout errors as % of total errors
- **Filter:** v2 traffic only (feature flag = true)
- **Time range:** 1-hour rolling
- **Visualization:** Stacked bar chart or pie (errors by type)
- **Purpose:** Helps diagnose root cause if error rate rises (e.g., "mostly 5xx" = backend issue, "mostly 4xx" = validation)
- **Success criteria:** Identify and act on specific error patterns fast

#### Panel 7: Redis Session Store Health
- **Metrics:** 
  - Session read latency (p99)
  - Session eviction rate (% of keys evicted)
  - Replication lag (async replica lag in ms)
- **Time range:** 1-minute rolling, updated every 10 seconds
- **Visualization:** Three panels stacked
- **Thresholds:**
  - Read latency p99: < 50ms (baseline ~10ms, alert if >100ms)
  - Eviction rate: < 0.1% (alert if >1%)
  - Replication lag: < 5000ms (alert if lag detected)
- **Success criteria:** Session store stays responsive under ramp load

### Dashboard Build Checklist
- [ ] Datadog dashboards created with all 7 panels
- [ ] Metrics instrumentation confirmed available in codebase (engineer owns verification)
- [ ] Staging test run: simulate 0% → 100% ramp in staging, verify all panels populate with data
- [ ] Alert thresholds tested against staging data (false-positive rate acceptable)
- [ ] Dashboard URLs finalized and added to runbook
- [ ] On-call team trained Friday morning on dashboard navigation and threshold meanings

---

## Automated Alerts

### Alert 1: v2 Error Rate Exceeds Baseline

| Property | Value |
|----------|-------|
| **Condition** | v2 error rate > (v1 baseline + 1%) for > 2 minutes |
| **Metric** | `checkout.error_rate{feature_flag: v2}` |
| **Baseline** | 30-day average of v1 error rate |
| **Threshold** | baseline + 1% (e.g., if v1 is 0.8%, alert at >1.8%) |
| **Duration** | 2 minutes (avoid flapping) |
| **Notification** | PagerDuty → ops-checkout, Slack → #ops-escalation |
| **Runbook link** | ramp_metrics_runbook (see below) |

### Alert 2: v2 Latency p99 Exceeds Threshold

| Property | Value |
|----------|-------|
| **Condition** | v2 latency p99 > (v1 baseline + 150ms) for > 5 minutes |
| **Metric** | `checkout.latency_p99{feature_flag: v2}` |
| **Baseline** | 30-day average of v1 latency p99 (assume ~1500ms) |
| **Threshold** | baseline + 150ms (e.g., alert at >1650ms) |
| **Duration** | 5 minutes (latency can spike transiently) |
| **Notification** | PagerDuty → ops-checkout, Slack → #ops-escalation |
| **Runbook link** | ramp_metrics_runbook |

### Alert 3: Coupon Endpoint Error Rate Spike

| Property | Value |
|----------|-------|
| **Condition** | `/v2/coupons/apply` error rate > 2% for > 2 minutes |
| **Metric** | `checkout.coupon_endpoint.error_rate{endpoint: /v2/coupons/apply}` |
| **Threshold** | 2% (new endpoint, low tolerance for errors) |
| **Duration** | 2 minutes |
| **Notification** | PagerDuty → ops-checkout, Slack → #ops-escalation |
| **Runbook link** | ramp_metrics_runbook |

### Alert 4: Redis Session Latency Spike

| Property | Value |
|----------|-------|
| **Condition** | Redis session read latency p99 > 100ms for > 1 minute |
| **Metric** | `redis.session_store.read_latency_p99` |
| **Threshold** | 100ms (baseline ~10ms, 10x increase is concerning) |
| **Duration** | 1 minute |
| **Notification** | PagerDuty → ops-checkout, Slack → #ops-escalation |
| **Runbook link** | ramp_metrics_runbook |

### Alert 5: Redis Replication Lag Detected

| Property | Value |
|----------|-------|
| **Condition** | Redis replication lag > 5 seconds |
| **Metric** | `redis.replication_lag_ms` |
| **Threshold** | 5000ms (indicates async replication is stalling) |
| **Notification** | PagerDuty → ops-checkout, Slack → #ops-escalation |
| **Runbook link** | ramp_metrics_runbook |

### Alert Build Checklist
- [ ] All 5 alerts created in Datadog/monitoring system
- [ ] PagerDuty routing to ops-checkout verified
- [ ] Slack integration to #ops-escalation tested
- [ ] Alert baselines calculated from v1 production data
- [ ] Staging test: trigger each alert manually, verify notification fires
- [ ] On-call team trained Friday on alert meanings and response protocol

---

## Go/No-Go Decision Criteria by Ramp Stage

Each ramp stage gate requires ops + engineer + PM consensus. Progression is halted if any metric is outside the criteria.

### Stage 1: 0% → 25% Ramp (Friday evening into Saturday)

**Criteria for progression (all must be true):**
- v2 conversion rate ≥ 95% of v1 baseline
- v2 error rate ≤ v1 baseline + 1%
- v2 latency p99 ≤ v1 baseline + 200ms
- Coupon endpoint success rate ≥ 98%
- Coupon endpoint latency p99 ≤ 500ms
- Redis session store latency p99 < 100ms
- No critical errors in logs (5xx, schema mismatch, OOM)

**Hold/rollback trigger:**
- v2 conversion rate < 90% of v1 baseline → pause ramp, investigate
- v2 error rate > v1 baseline + 2% → pause ramp, investigate
- Coupon success rate < 95% → pause ramp, investigate coupon endpoint
- Redis replication lag detected or session latency > 200ms → page DBA, assess failover risk

**Decision if held:** After 30-minute investigation, PM decides: resume or rollback

### Stage 2: 25% → 50% Ramp (Saturday into Sunday)

**Criteria for progression (all must be true):**
- v2 conversion rate ≥ 95% of v1 baseline (no degradation vs Stage 1)
- v2 error rate ≤ v1 baseline + 1.5% (slightly higher tolerance due to higher load)
- v2 latency p99 ≤ v1 baseline + 150ms (tightening as system stabilizes)
- Coupon endpoint success rate ≥ 99%
- Coupon endpoint latency p99 ≤ 400ms
- Redis session eviction rate < 0.1%
- No schema mismatch errors
- No duplicate transactions in audit log

**Hold/rollback trigger:**
- Any metric fails to improve from Stage 1 OR worsens → pause
- Signs of Redis memory pressure or connection pool exhaustion → pause, consult engineer
- Idempotency-key misses detected → immediate escalation to engineer + compliance

**Decision if held:** After 30-minute investigation, PM decides: resume or rollback

### Stage 3: 50% → 100% Ramp (Sunday into Monday)

**Criteria for progression (all must be true):**
- v2 conversion rate ≥ 97% of v1 baseline (expect stability at higher load)
- v2 error rate ≤ v1 baseline + 1% (must match v1 performance)
- v2 latency p99 ≤ v1 baseline + 100ms (system should be fully optimized)
- Coupon endpoint success rate ≥ 99.5%
- Coupon endpoint latency p99 ≤ 300ms
- Redis session store eviction rate < 0.05%
- Zero schema mismatch errors for 2+ hours
- Zero audit-log integrity warnings for 2+ hours

**Hold/rollback trigger:**
- v2 error rate > v1 baseline + 1.5% → pause ramp at current stage
- Latency p99 regresses > 200ms → pause ramp
- Coupon endpoint success rate drops below 99% → pause ramp, investigate endpoint
- Session latency p99 > 150ms for > 2 minutes → page DBA, assess Redis health

**Decision if held:** After 30-minute investigation, PM + ops + engineer vote on resume vs. rollback

### Final Gate: 100% Ramp Completion (Monday end of day)

**Success criteria:**
- v2 conversion rate ≥ 98% of v1 baseline
- v2 error rate ≤ v1 baseline (v1 and v2 error rates are equivalent)
- v2 latency p99 ≤ v1 baseline + 50ms (v2 performance is comparable to v1)
- No alert flapping for ≥ 4 hours
- Audit log integrity: zero duplicates, zero missing idempotency keys
- Support ticket volume (coupon/session related) ≤ historical baseline + 5%

**Outcome:** PM declares v2 ramp complete OR orders rollback

---

## Ramp Metrics Runbook

### If Alert Fires (Error Rate, Latency, Coupon, or Redis Alert)

**Immediate (ops, minute 0–2):**
1. Acknowledge alert in PagerDuty
2. Open the `Checkout v2 Ramp — Metrics Comparison` dashboard
3. Verify alert is not a false positive:
   - Check which metric triggered (error rate, latency, coupon success, Redis lag)
   - Look at the v1 baseline on same panel — is v1 also elevated? (If yes, shared issue, not v2-specific)
   - If v2 is degraded and v1 is normal, proceed to step 4
4. Page engineer immediately: "Checkout v2 ramp alert: [metric] on [endpoint]. Check dashboard. v2 vs v1 comparison at [dashboard_url]."
5. Post in #ops-escalation: "[ALERT] v2 [metric] exceeded threshold at [time]. [value]. Page [engineer]. Dashboard: [url]."

**Engineer response (minute 2–5):**
1. Engineer pulls Datadog dashboard, confirms v2 degradation vs. v1
2. Engineer checks recent deployment/flag change logs
3. Engineer diagnoses: Is this v2 code issue (query, endpoint logic, new dependency latency) or shared issue (database, shared service)?
4. If v2-specific: engineer responds in Slack with assessment: "Root cause: [brief description]. Recommendation: [pause/rollback/investigate further]."

**Ops decision (minute 5–10):**
1. If engineer says "investigate further, may be transient": ops monitors metric for 5 more minutes. If alert clears, continue ramp. If alert persists, proceed to escalation.
2. If engineer says "this is a v2 issue": ops escalates to PM: "@PM — v2 ramp alert confirmed. [metric] degradation. Engineer assessment: [brief]. Recommend: [pause/rollback]. Your call?"
3. If engineer says "this looks like shared issue (not v2-specific)": ops handles as normal incident (not ramp-gating). Continue ramp.

**PM decision (minute 10–15):**
- **If PM says "pause":** Ops immediately toggles feature flag to hold at current % (do not ramp to next stage). Engineer investigates for 30 minutes. If fix is identified and < 30 min to deploy, apply fix and resume. If uncertain, PM decides: resume or rollback.
- **If PM says "rollback":** Ops flips flag to 0% (v1 only). Engineer assesses rollback for schema/audit issues. Escalate to compliance if duplicates or mismatches detected.
- **If PM is unreachable within 15 minutes:** Ops pauses ramp (hold at current %) and escalates to PM's manager and tech lead.

### If Alert Fires During Autonomous Ramp Window (Friday night, when PM sleeping)

Ops has authority to pause ramp without waiting for PM. Escalate to PM first thing via Slack + phone, but do not wait for approval.

- Alert confirms v2 issue (engineer validated)
- Ops pauses ramp (toggles flag to current %, does not proceed to next stage)
- Ops pages engineer to investigate root cause
- Ops notifies PM: "Paused v2 ramp at [%] due to [metric]. [Status]. Will resume after 30-min investigation or escalate to you."

### If Multiple Alerts Fire Simultaneously

1. Acknowledge all alerts
2. Page engineer immediately
3. Ops checks if this is coordinated (all from v2) or distributed (v1 + v2 both affected):
   - All v2: v2-specific issue, escalate to PM
   - Distributed: shared system issue, ops treats as normal incident (not ramp-gating)
4. In Slack: "Multiple alerts: [list]. v2-specific: [yes/no]. [Diagnosis in progress]."

### If Metrics Dashboard is Unavailable or Stale

1. Ops pages engineer and Datadog/monitoring team
2. ops pauses ramp immediately until dashboard is restored (no go/no-go decision without visibility)
3. Escalate to PM: "Dashboard is [unavailable/stale]. Pausing ramp until metrics restored."

### Post-Alert Analysis (after ramp)

After each ramp stage, ops + engineer review all alerts that fired:
- Were they actionable (did they surface a real issue)?
- Were they noisy (false positives)?
- Did the threshold need adjustment?
Document findings in the ramp retro.

---

## Owner Assignments and Deadlines

| Deliverable | Owner | Deadline |
|-------------|-------|----------|
| Datadog dashboards (7 panels) | Engineer (metrics instrumentation) | Friday morning |
| Metric baselines (v1 30-day average) | Ops | Friday morning |
| Alert configuration (5 alerts in Datadog) | Ops | Friday morning |
| PagerDuty + Slack routing tests | Ops | Friday afternoon |
| Staging end-to-end test (0%→100% ramp simulation) | Engineer | Friday afternoon |
| Alert false-positive rate assessment | Ops + Engineer | Friday afternoon |
| On-call team training (dashboard + alert meanings) | Ops | Friday morning |
| Dashboard link in runbook + decision_authority.md | Ops | Friday afternoon |

---

## Testing Checklist (Friday before ramp)

### Datadog Dashboard Test
- [ ] All 7 panels are visible and populating with data
- [ ] v1 baseline (historical) is clearly marked and visible
- [ ] v2 live data (current) is updating every 5 minutes
- [ ] Threshold annotations (red/yellow zones) are visible
- [ ] Dashboard loads in <3 seconds from bookmarked link
- [ ] Mobile view is readable (for on-call checking phone)

### Alert Test (in staging)
- [ ] Alert 1 (v2 error rate): trigger manually, confirm PagerDuty page fires and Slack notification appears
- [ ] Alert 2 (v2 latency p99): confirm fires and routes correctly
- [ ] Alert 3 (coupon endpoint): confirm fires and routes correctly
- [ ] Alert 4 (Redis session latency): confirm fires and routes correctly
- [ ] Alert 5 (Redis replication lag): confirm fires and routes correctly
- [ ] False-positive rate: simulate normal ramp load, run for 30 minutes, expect < 1 false page

### Runbook Test
- [ ] Ops can pull up dashboard from runbook link in < 10 seconds
- [ ] Engineer can navigate to v1 vs v2 comparison panels and understand thresholds
- [ ] Ops + engineer can manually trigger an alert and walk through decision script together
- [ ] Decision script covers all alert types and decision paths (pause, rollback, investigate)

---

## Escalation During Ramp

If metrics are unclear, inconclusive, or dashboard is down:
- **Escalate to engineer:** "Metrics don't tell us if v2 is degraded. Can you compare error rates manually?"
- **Escalate to PM:** "No clear signal for go/no-go at [stage]. Recommend [pause/proceed with caution]."
- **Escalate to exec:** "Ramp stalled due to metric visibility gap. Delaying decision by [X minutes]."

---

## Success Definition

By Friday before ramp:
- Dashboard is live, tested, and ops can navigate it with eyes closed
- All 5 alerts are armed, tested, and non-flapping
- Go/no-go criteria are clearly understood by ops, engineer, and PM
- Runbook is clear: ops knows exactly what to do if alert fires

By Monday after ramp completion:
- v2 metrics are on par with v1 (error rate ≤ v1 baseline, latency within 50ms)
- All ramp stages completed without rollback
- Support ticket volume is within baseline + 5%
- Audit log integrity is clean (zero duplicates, zero missing keys)
