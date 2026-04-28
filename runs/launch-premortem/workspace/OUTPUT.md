# Pre-mortem Results — Checkout Refactor Launch

**Launch:** Friday 2026-04-24, feature-flagged OFF. Ramp to 100% Monday 2026-04-27.  
**Pre-mortem date:** Tuesday 2026-04-22  
**Scope:** Payments API v2 + new React checkout flow, coupon endpoint added this week  
**Team:** Engineer, Ops, Support (PM facilitator)

---

## Top Risks (Prioritized by Impact × Likelihood)

### 1. **Coupon endpoint /v2/coupons/apply — under-tested, unmonitored, unbriefed**
- **Likelihood:** High | **Impact:** High
- **Mechanism:** New endpoint added this week, never saw production traffic. Real coupon codes (legacy formats, edge cases), user patterns, and cart edge cases untested. Support team has no briefing on v2 error messages or validation changes. Ops has no dashboard visibility. When users hit coupon errors Sunday/Monday, the system will be blind.
- **Early signal:** Error spike in `/v2/coupons/apply` logs (5xx, 4xx, timeouts). Support reports "coupon didn't apply" or "code won't work" tickets clustering by code format. Help-center article search for "coupon" spikes.
- **Mitigation:**
  - **Engineer:** Production data audit (50–100 real coupon codes tested against v2 staging), smoke tests for edge cases, instrumentation deployed (success rate, latency, error breakdown metrics). **Due Thu 2 PM.**
  - **Ops:** Dashboard panels live (success rate, error types, latency p50/p95/p99), alerts on success rate <95% and latency >500ms, runbook with troubleshooting decision tree. **Due Thu 5 PM.**
  - **Support:** 30-min briefing with engineer Thu 2 PM, error code documentation, help-center articles updated, agent training Fri morning. **Due Thu 5 PM.**
- **Owner:** Engineer + Ops + Support (joint responsibility)

---

### 2. **Redis session store — latency spike during ramp OR async replication failover**
- **Likelihood:** Med-High | **Impact:** High
- **Mechanism:** Single-node Redis per region, session-heavy v2 flow (coupon choice, payment method stored in session). During Monday's 0%→100% traffic ramp, session dataset grows. If single node hits memory pressure, eviction policy triggers, or connection pool bottleneck occurs, session reads fail or timeout. Either checkouts block indefinitely (HTTP 504), or sessions are evicted (idempotency-key lost, duplicate transactions allowed). Async replication failover Friday–Sunday could lose data in the failover window.
- **Early signal:** Redis session read latency p99 jumps from <10ms to >100ms. Redis eviction stats spike. Session read error rate increases. Checkout timeout rate climbs during ramp. Redis replication lag spike detected.
- **Mitigation:**
  - **Engineer:** Load test new session re-read frequency in staging (simulate Monday traffic), deploy circuit breaker on session-read timeouts (fail gracefully to cached session or defer idempotency check). **Due Thu.**
  - **Ops:** Alert on Redis session latency p99 >100ms for >1 min (page ops-checkout). Alert on replication lag >5s. Failover test Friday afternoon after ship, verify alert triggers and on-call recovery steps. **Due Fri afternoon.**
  - **Runbook:** Manual failover promotion steps, flag-flip-to-v1 procedure documented.
- **Owner:** Engineer + Ops

---

### 3. **Ramp metrics blind to v2 degradation — no stratified dashboards, no alerts, no go/no-go signal**
- **Likelihood:** High | **Impact:** High
- **(REBALANCED from "med" to "high" — metrics gate rollback decisions; blinded metrics = delayed rollback = extended user pain)**
- **Mechanism:** Current state: blended v1+v2 metrics reported as aggregates. If v2 is 2% worse on conversion, signal is noise in blended average. By 50% ramp, degradation might not be visible. By 100%, rollback decision is delayed by 30–60 min. Ramp stages (0%→25%→50%→100%) have no clear go/no-go criteria because PM/ops cannot see stratified data.
- **Early signal:** Lack of v2-only dashboard panels. Blended conversion/latency show no clear regression. Ops unable to answer "is v2 measurably worse than v1?" with yes/no. On-call team questions signal quality.
- **Mitigation:**
  - **Engineer:** Metrics instrumentation confirmed (v1 vs v2 checkout success rate, latency p50/p95/p99, coupon endpoint metrics, Redis session store health). **Due Fri morning.**
  - **Ops:** Build stratified dashboard (7 panels: v1 vs v2 conversion, error rate, latency, coupon success/latency, Redis health). Set 5 automated alerts (v2 error >baseline+1%, latency >baseline+150ms, coupon error >2%, Redis latency >100ms, replication lag >5s). Test alerts Friday afternoon. Define go/no-go criteria per ramp stage (Stage 1: v2 error ≤ +1%, latency ≤ +200ms; Stage 2: ≤ +1.5%, ≤ +150ms; Stage 3: ≤ +1%, ≤ +100ms). **Due Fri 5 PM.**
  - **Runbook:** If alert fires during ramp, ops pages engineer with dashboard link + full context (v1 vs v2 comparison), engineer confirms v2-specific degradation, ops escalates to PM with recommendation (pause/rollback). Decision within 15 min.
- **Owner:** Ops (primary), Engineer (metrics)

---

### 4. **Feedback loop lag — support detects bugs first, ops doesn't notice pattern until 60+ minutes later**
- **Likelihood:** High | **Impact:** Med-High
- **(REBALANCED from "med" to "high" — this is the CANARY signal; if monitoring is blind, support escalation is the only early warning)**
- **Mechanism:** Past pattern: tickets are first signal. If coupon endpoint silently fails for certain code formats, or checkout has subtle issues, support will see "coupon didn't apply" tickets 20–60 minutes before monitoring alerts fire (if alerts even exist). Without structured escalation, support spends time manually determining pattern (5+ similar tickets), then pings Slack ad-hoc at 60+ min mark. By then, ops has already investigated other alerts, customer pain is high, and response is slower.
- **Early signal:** Monday morning, support queue fills with 5+ tickets containing identical keywords ("coupon," "session," "payment") within 1–2 hour window. Agents notice pattern before ops dashboard alerts.
- **Mitigation:**
  - **Support + Ops:** Define escalation threshold (5+ tickets with same keyword in 1 hour) and channel (#ops-escalation, required format: "[PATTERN] keyword, N tickets in last 60 min, first 3 tickets attached"). Ops commits to 15-min triage SLA (ack within 5 min, diagnosis within 15 min). Bridge channel (#checkout-launch-ops) for off-hours escalation. **Live by Fri ship.**
  - **Support briefing:** Fri 14:00 UTC (2 hours before ship), all agents trained on threshold, keywords to monitor (coupon, session, payment, error, timeout), escalation format, and response expectations. **Done Fri 2 PM.**
  - **Ops secondary briefing:** If ops-primary is unreachable >5 min, eng-secondary checks #ops-escalation, validates signal in dashboard, escalates to ops-primary or #checkout-launch-ops. **Thu 1 PM.**
  - **Runbook:** Ops response decision tree (Category A: real issue confirmed by metrics → page engineer; Category B: ambiguous → escalate to engineer for deeper look; Category C: false positive → provide response template to support).
- **Owner:** Ops (primary), Support (pattern detection & escalation)

---

### 5. **Idempotency-key enforcement broken during flag transitions**
- **Likelihood:** Med-High | **Impact:** High
- **Mechanism:** Idempotency-key enforcement is enabled on `/v2/transactions` but not on v1. During ramp, some users route to v2 (enforcement active), some to v1 (no enforcement). If network/retry logic routes same user request to v1 after v2, or vice versa, the duplicate is not rejected. Post-ramp, if flag flips OFF to rollback, v1 processes transactions that v2 already recorded (v1 has no record of the idempotency key, so it sees request as new). Result: duplicate transactions in ledger; compliance audit log shows duplicate transaction IDs for same user+timestamp. Silent duplicate charges possible.
- **Early signal:** Duplicate transaction records in audit log (same idempotency-key ID, same user, milliseconds apart). Mismatch in transaction count totals between v2 and v1 code path views. Customer escalations about double charges. Audit log validation tool flags duplicates.
- **Mitigation:**
  - **Engineer:** Integration test that toggles flag OFF after v2 traffic, then attempts duplicate transaction, verifies it is rejected. Audit v1 code path to confirm idempotency keys are not re-applied if traffic re-routes v1→v2→v1. Add v1 idempotency guard: before v1 processes a request, query audit log for (user_id, idempotency_key) within last 24h; if found, reject with 409 Conflict. **Due Thu.**
  - **Ops + Compliance:** Post-ramp audit verifies zero duplicates in audit log (Monday 23:00 UTC). If audit fails, escalate to compliance + legal; initiate data repair (see Section 2 below).
  - **Runbook:** Ops monitors audit log for duplicate patterns during ramp. If duplicates detected, escalate to engineer + compliance immediately.
- **Owner:** Engineer (implementation), Ops (monitoring), Compliance (sign-off)

---

### 6. **Feature flag control-plane availability + v1 schema compatibility on rollback**
- **Likelihood:** Med | **Impact:** High
- **Mechanism:** Feature flag control plane is critical for 0%→100% ramp. If flag service is unavailable, slow, or returns stale state, ramp cannot proceed as intended. Some regions on v2, others on v1, inconsistent UX. Also: v2 migration has already run. If Friday or Monday ramp goes badly and we flip flag OFF, v1 code runs against v2-migrated schema. If v1 expects pre-migration columns, it throws "column not found" errors. If v2 migration added NOT NULL constraints, v1 inserts fail. Rollback becomes impossible without data repair.
- **Early signal:** Flag evaluator latency spike or error rate spike. Users on same account see different checkout flows. v1 errors post-flag-flip (SQL: column not found, constraint violations). Rollback fails partway, system stuck.
- **Mitigation:**
  - **Engineer:** Run full rollback test in staging (apply v2 migration, enable flag with v2 traffic, flip OFF, execute regression suite of v1 transactions). Document any schema incompatibilities; either fix now or plan pre-rollback data migration. Test report: "v1 can safely run against v2-migrated schema" ✓ or ✗. **Due Thu 2 PM.**
  - **Ops:** Flag control-plane failover test Friday 17:00 UTC (after ship, before ramp). Verify alert fires if flag service latency >500ms or error rate >1%. Verify on-call can force rollback manually (flag service unavailable scenario). Add runbook section: flag failover steps, manual flag commands, rollback procedure. **Due Fri afternoon.**
  - **Runbook:** If flag service unavailable during ramp, ops has manual procedures to (a) force flag state, (b) initiate rollback without flag service.
- **Owner:** Engineer (schema testing), Ops (flag failover test)

---

### 7. **Thin on-call coverage Friday night through Sunday ramp**
- **Likelihood:** High | **Impact:** Med
- **Mechanism:** Friday ship is 16:00 UTC. Ops primary is on-call for weekend (me). Backend engineer is secondary. No dedicated incident commander, no secondary ops pager. If issue surfaces Friday evening (18:00 UTC) and first signal is support-ticket spike (45–60 min later), ops-primary might be in another incident or asleep. Escalation is slow; decision lag extends downtime.
- **Early signal:** Support-ticket volume spike 20–60 min post-impact. Slack mentions from support team. If no structured escalation, ops stays unaware.
- **Mitigation:**
  - **Ops:** Eng-secondary briefed on escalation paths (do not page eng on-call for customer issues; check #ops-escalation for support patterns, do quick metric check, DM ops-primary if urgent). Set phone alarm for 15-min check-ins Fri night + Sat/Sun. Commit to 5-min acknowledgment, 15-min triage SLA on #ops-escalation. **Done Thu 1 PM + Fri setup.**
  - **Support:** Use #checkout-launch-ops bridge channel as fallback for off-hours escalation. Escalate at 5-ticket threshold (don't wait for ops-primary). Ops monitors both channels. **Live by Fri ship.**
  - **Decision authority:** Documented (see Section 2). Autonomous rollback rules for critical failures (system losing money, data, or audit-log integrity). **Done in t_005.**
- **Owner:** Ops (coverage commitment), Engineer (secondary availability)

---

### 8. **Audit log integrity & compliance verification**
- **Likelihood:** Med | **Impact:** High
- **Mechanism:** Project context requires "clean audit log for all transactions Monday onward." If idempotency enforcement fails (risk #5), duplicates appear in audit log. If rollback is partial or incomplete, v1 and v2 transactions may be interleaved or duplicated. Compliance attestation on Tuesday depends on clean audit log Monday night. If audit fails and we have duplicates, remediation (data repair, refunds) is complex and time-consuming.
- **Early signal:** Post-ramp audit (Monday 23:00 UTC) detects duplicates, missing idempotency keys, or timestamp inversions.
- **Mitigation:**
  - **Engineer + Ops + Compliance:** Pre-launch (Thu): Define "clean audit log" criteria (no duplicates, all v2 transactions have idempotency keys, timestamps monotonic, reconcilable v1↔v2 boundary, no orphaned records). Build and test audit verification script (synthetic v2 data). **Due Thu EOD.**
  - **Post-ramp audit (Monday 23:00 UTC):** Engineer runs verification script, compliance officer evaluates results. PASS → ship. FAIL (Minor: <5 dups, <0.1% rate) → repair + refund. FAIL (Critical: >10 dups, >0.1% rate) → rollback. **Due Mon evening.**
  - **Rollback scenarios:** If rollback during ramp (Scenario A) or after ramp (Scenario B), v1 idempotency guard prevents re-processing same key. Post-rollback reconciliation queries verify no new duplicates. Refund process for any duplicates. **Procedures in rollback_integrity_plan.md.**
- **Owner:** Engineer + Ops + Compliance (joint)

---

### 9. **PM availability & decision authority (Thu–Mon)**
- **Likelihood:** Med | **Impact:** Med
- **Mechanism:** PM is out Tue–Wed, back Thursday. Friday ship, Fri–Sun ramp, Monday ramp completion all happen while PM has limited availability (sleeping, thin hours). If a critical go/no-go decision (e.g., pause ramp, rollback?) is needed Friday night or Sunday, who decides? Who escalates to exec/legal if needed?
- **Early signal:** Ramp metrics ambiguous or alert fires. Ops can't reach PM within 15 min. Decision is delayed, user pain extends.
- **Mitigation:**
  - **Ops:** Document decision authority chain (ops primary → engineer secondary → PM escalation for ramp decisions). Define autonomous rollback rules (ops can rollback immediately if system losing money/data, notify PM after). Confirm PM on-call phone/Slack Friday evening. Document executive escalation triggers (audit-log integrity issue, customer data loss, revenue impact >5% error rate). **Done in t_005.**
  - **Runbook:** If PM unreachable within 15 min, ops can pause ramp (hold at current %) but cannot rollback without PM approval (unless autonomous trigger). Escalate to PM's manager + CTO if needed.
- **Owner:** Ops (escalation coordinator)

---

### 10. **Data reconciliation & rollback failure scenario (incomplete rollback, mixed v1/v2 state)**
- **Likelihood:** Low | **Impact:** High
- **Mechanism:** If rollback is initiated but fails partway (e.g., v1 schema issue discovered mid-rollback, flag flip succeeds but v1 transactions error), system is stuck with mixed state: some v2 transactions completed, some v1 attempts partially failed. Audit log is inconsistent. Ledger integrity unknown. Data repair is manual and complex.
- **Early signal:** v1 errors post-flag-flip (schema mismatch, constraint violation). Rollback status unclear. DBA reports data inconsistency.
- **Mitigation:**
  - **Engineer + Data engineer:** Build post-rollback reconciliation queries (transaction counts, idempotency duplication check, timestamp monotonicity, amount reconciliation, orphaned-record detection). Test in staging. **Due Thu EOD.**
  - **Data engineer:** Duplicate cleanup procedures documented (classify duplicate type, decide action per duplicate, execute cleanup with audit trail, issue refunds, update audit log with suppression reason). **Due Thu EOD.**
  - **Runbook:** If rollback is incomplete, pause all checkout traffic immediately. Resolve the blocker (schema fix or v1 revert). Once resolved, resume. Post-resolution, run reconciliation queries to verify no orphans or duplicates. **In rollback_integrity_plan.md.**
- **Owner:** Engineer + Data engineer + Ops + Compliance

---

## Risks Considered But Deprioritized

### **Outdated help-center articles** (Likelihood: High, Impact: Med)
- **Reason:** Tactically important but bounded impact. Support team can audit and fix Thursday EOD (included in consolidated_coupon_plan). Not a system failure. Dropped from top-risk list because it's self-serviceable by Friday morning.

### **Weekend staffing bottleneck** (Likelihood: High, Impact: stated High, but actually Med)
- **Reason:** This is a capacity problem, not a technical risk. Self-serviceable: support lead can schedule 4 agents Monday 7 AM–2 PM instead of normal 2–3. Staffing decision made by support, not a blocker. Included in consolidated_coupon_plan; does not require technical mitigation. Dropped because it's pre-emptively solved.

### **Session re-auth / unexpected logout mid-checkout** (Likelihood: Med-High, Impact: High)
- **Reason:** User-facing symptom, not a root cause. Root cause is Redis session latency (risk #2). Treating Redis latency addresses this. Kept in consolidated_coupon_plan (engineer confirms behavior change, supports team briefed on user messaging).

### **Runbook gaps** (Likelihood: High, Impact: Med)
- **Reason:** On-call friction, not system failure. Runbook update is straightforward. Included in consolidated_coupon_plan; dropped from top-risk list because it's operationally important but not a technical blocker.

---

## Gaps Surfaced & Resolved

### **Gap 1: Compliance / Audit Log Integrity**
- **Why it was missed:** Engineer flagged idempotency-enforcement failures as a failure mode, but nobody explicitly owned the question: "Are we confident the audit log will be clean Monday?"
- **What we're doing:** audit_log_compliance_plan.md (t_004) defines "clean" audit log, post-ramp verification procedure (Monday 23:00 UTC), rollback scenarios, and data repair steps. Compliance officer signs off on thresholds (pass/fail/critical-fail). Engineer builds and tests verification script.
- **Owner:** Engineer + Ops + Compliance

### **Gap 2: PM Availability & Decision Authority (Thu–Mon)**
- **Why it was missed:** No role flagged the dependency: PM out Tue–Wed, back Thursday, then thin availability Fri–Sun while ramp happens. Who decides if rollback is needed?
- **What we're doing:** decision_authority.md (t_005) documents decision-making chain, autonomous rollback rules for critical failures, executive escalation triggers. PM on-call confirmed Friday evening. Ops has authority to pause ramp without PM approval, but requires PM approval for rollback (except autonomous scenarios).
- **Owner:** Ops (escalation coordinator)

### **Gap 3: Post-Launch Success Metrics (Days 2–7)**
- **Why it was missed:** Engineer flagged ramp metrics (0%→100%), but nobody specified: "What are we watching Wednesday–Friday to know the launch is successful?"
- **What we're doing:** ramp_metrics_plan.md defines go/no-go criteria for ramp completion (v2 error rate ≤ v1 baseline, latency within 50ms, no alert flapping >4 hrs). Post-launch success criteria are implicit in final gate (audit log clean, support ticket volume within baseline + 5%). Ops commits to ongoing monitoring.
- **Owner:** Ops + Engineer (ongoing)

### **Gap 4: Data Reconciliation & Rollback Safety**
- **Why it was missed:** Engineer mentioned schema incompatibility as a failure mode, idempotency dups in audit log, but nobody surfaced: "If rollback is partial or incomplete, how do we reconcile v1 vs v2 ledgers? Who owns cleanup?"
- **What we're doing:** rollback_integrity_plan.md (t_009) documents staging test (apply v2 migration, ramp v2 traffic, flip flag OFF, verify v1 succeeds), data reconciliation queries (counts, duplicates, amounts, timestamps), and duplicate cleanup procedures (classification, refunds, audit trail).
- **Owner:** Engineer + Data engineer + Ops + Compliance

### **Gap 5: Customer Communications & Rollback Messaging**
- **Why it was missed:** No dedicated marketing/comms reviewer on pre-mortem. Nobody raised: "If rollback happens, what do we tell customers?"
- **What we're doing:** rollback_comms_plan.md (t_010) documents Tier 1 notification (affected users, within 30 min of rollback), Tier 2 broadcast (all users, 1–4 hours), support FAQ, and escalation workflow.
- **Owner:** Support lead

---

## This Week's Mitigation Commitments (Due Friday EOD)

### **Engineer**
- [ ] Coupon endpoint production data audit + smoke tests (Tue–Thu)
- [ ] Coupon endpoint instrumentation deployed (success rate, latency, error breakdown metrics) (Thu)
- [ ] Error code documentation for all v2 coupon responses (Thu 10 AM)
- [ ] Metric baselines defined (expected success rate, latency, error rates) (Thu 11 AM)
- [ ] Idempotency-key integration test + v1 guard implementation (flag toggle OFF, verify dups rejected) (Thu)
- [ ] v1 schema compatibility test in staging (apply v2 migration, flip flag OFF, verify v1 transactions succeed) (Thu morning)
- [ ] Rollback test report signed off (schema compatibility PASS/FAIL) (Thu 2 PM)
- [ ] Audit log verification script built + tested with synthetic v2 data (Thu EOD)
- **Dependencies on:** Load test of Redis + coupon endpoint; stage all tests; completion gates Friday ship approval

### **Ops**
- [ ] Coupon endpoint dashboard (5 panels) live in Datadog (Thu 5 PM)
- [ ] Ramp metrics dashboard (7 panels: v1 vs v2 conversion/error/latency, coupon, Redis) live (Thu 5 PM)
- [ ] 5 alerts configured (v2 error, latency, coupon success, Redis latency, replication lag) + tested in staging (Thu 5 PM)
- [ ] Runbook updated with v2-specific sections (error codes, troubleshooting, rollback procedure) (Thu 5 PM)
- [ ] Support escalation protocol live: #ops-escalation channel, 5-ticket threshold, 15-min SLA confirmed (Thu EOD)
- [ ] Decision authority document signed (PM on-call confirmed, escalation contact list, autonomous rollback rules) (Thu EOD)
- [ ] Redis failover test scheduled Friday 17:00 UTC (after ship, verify alert + recovery steps) (Fri afternoon)
- [ ] On-call team training: dashboard + alert meanings + decision script (Fri 10 AM)
- [ ] 15-min monitoring commitment: #ops-escalation + #checkout-launch-ops checked every 15 min (Fri–Mon)
- **Dependencies on:** Engineer metrics ready; Datadog API access; PagerDuty routing tested

### **Support**
- [ ] Coupon endpoint briefing with engineer (30 min, Thu 2 PM)
- [ ] Internal quick reference guide (1 page: error codes, decision tree, escalation criteria) (Thu 3 PM)
- [ ] Help-center article audit (coupon, session, error articles) + updates (v2 error codes, behavior) (Thu 4 PM)
- [ ] Agent training notes for Friday morning standup (Thu EOD)
- [ ] Monday staffing: 4 agents scheduled 7 AM–2 PM (instead of normal 2–3) (Thu EOD)
- [ ] Escalation protocol briefing: all support + weekend staff trained on #ops-escalation + format (Fri 2 PM, 30 min)
- [ ] Rollback comms plan: Tier 1 + Tier 2 messages drafted, approved, ready to send (Thu EOD)
- [ ] Rollback FAQ ready for agent use (Thu EOD)
- **Dependencies on:** Engineer error codes; ops escalation protocol ready; PM approval on messaging

### **Compliance**
- [ ] Audit log definition: Sign-off on "clean audit log" criteria (Thu EOD)
- [ ] Audit verification thresholds: Pass/fail/critical-fail criteria + script validated (Thu EOD)
- [ ] Rollback cleanup procedures: Approval of duplicate classification + refund process (Thu EOD)
- [ ] Monday night post-ramp audit: Verify clean audit log, sign-off on PASS/FAIL (Mon 23:00 UTC)

---

## What We'll Watch in the Week After Launch (Tue 2026-04-28 – Fri 2026-05-01)

### **Continuous Monitoring (Ops)**
- **Ramp metrics dashboard:** v2 error rate, latency p99, coupon success rate, Redis health all within go/no-go thresholds
- **Alerts:** No alert flapping (expected spikes within threshold, no sustained degradation)
- **Support ticket patterns:** Coupon, session, payment keyword volume within baseline + 5%
- **Audit log integrity:** Zero duplicates, all transactions reconcilable

### **Early Signal Checks (Support + Ops)**
- **Daily:** Review support ticket volume for coupon/session/payment keyword spikes. If pattern emerges, post to #ops-escalation.
- **Daily:** Ops checks dashboard for any anomalies (latency creep, error rate drift, cache hit rate drops)
- **Tuesday (PM returns):** All-hands debrief: what went smoothly, what surprised us, what to fix next time

### **Post-Ramp Audit (Mon night)**
- **Compliance + Engineer:** Verify clean audit log (zero duplicates, all v2 transactions have idempotency keys, timestamps monotonic)
- **Data engineer + Finance:** Amount reconciliation (v1 + v2 totals match external ledger)
- **Ops + Engineer:** Review all alerts that fired during ramp (were they actionable? noisy? thresholds correct?)

### **Rollback Scenario (if triggered)**
- **Immediate:** Tier 1 customer notification within 30 min
- **Within 4 hours:** Tier 2 broadcast + FAQ + support readiness
- **Post-rollback:** Data reconciliation (duplicate cleanup, refund processing), audit trail
- **Post-incident:** Root cause investigation, code fix, decision on re-launch timeline

---

## Sign-Off Checklist (Friday EOD)

- [ ] **Engineer:** Coupon endpoint audit PASS, v1 schema compatibility PASS, all instrumentation deployed
- [ ] **Ops:** Dashboards live, alerts tested non-flapping, runbook complete, team trained
- [ ] **Support:** Briefing complete, help-center updated, Monday staffing confirmed, escalation protocol live
- [ ] **Compliance:** Audit log definition approved, thresholds set, verification script ready
- [ ] **PM:** Go/no-go decision on Friday ship

---

## Launch Timeline

- **Friday 16:00 UTC:** Ship (feature flag OFF, 0% ramp)
- **Friday 17:00 UTC:** Ops flag failover test (verify alert + manual recovery)
- **Friday 18:00 UTC:** On-call check-in (ops + engineer + support confirm dashboards live, ready for weekend)
- **Friday 18:30 – Monday 18:00 UTC:** Ramp window (0% → 25% Sat → 50% Sun → 100% Mon)
  - Ramp gates: At each stage, metrics must pass go/no-go criteria (v2 error ≤ baseline + 1%, latency within threshold)
  - Support escalation: If 5+ tickets same keyword in 1 hour, post to #ops-escalation, ops responds within 15 min
  - Rollback authority: PM + ops + engineer consensus to pause or rollback
- **Monday 23:00 UTC:** Post-ramp audit (verify clean audit log, compliance sign-off PASS/FAIL/CRITICAL-FAIL)
- **Tuesday morning:** PM returns; all-hands debrief

---

## Key Decision Points

1. **Thursday EOD:** PM approves mitigation readiness (coupon audit, dashboards, runbook, briefings)
2. **Friday 16:00 UTC:** Ship green light (all checklists checked, on-call aware, dashboards live)
3. **Ramp gates (Fri–Sun):** PM + ops + engineer vote to proceed or pause/rollback at each stage
4. **Monday 23:00 UTC:** Compliance audit result (PASS → v2 live; FAIL (Minor) → repair; FAIL (Critical) → rollback)
5. **Tuesday morning:** Post-launch retro and decision on next v2 iteration timeline

---

## Appendix: Risk Sources

| Risk | Raised By | Consolidated Across |
|------|-----------|-------------------|
| Coupon endpoint | Engineer + Ops + Support | Testing + Monitoring + Briefing (t_006) |
| Redis session | Engineer + Ops | Latency + Failover (t_007 + t_008) |
| Ramp metrics | Engineer + Ops | Stratified dashboard + alerts (t_007) |
| Feedback loop | Support + Ops | Escalation protocol (t_008) |
| Idempotency enforcement | Engineer | Implementation + Compliance (t_004 + t_009) |
| Feature flag / schema | Engineer + Ops | Failover + Rollback integrity (t_005 + t_009) |
| Thin on-call | Ops | Decision authority + secondary briefing (t_005) |
| Audit log integrity | (Gap surfaced by lead) | Compliance plan (t_004) |
| PM availability | (Gap surfaced by lead) | Decision authority (t_005) |
| Data reconciliation | (Gap surfaced by lead) | Rollback integrity (t_009) |
| Comms / rollback | (Gap surfaced by lead) | Rollback comms plan (t_010) |

---

**Prepared by:** Team Lead (PM facilitator)  
**Pre-mortem date:** Tuesday 2026-04-22  
**All deliverables due:** Friday 2026-04-24, 16:00 UTC (ship time)  
**This plan is a blocker for Friday launch.**