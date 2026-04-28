# Consolidated Coupon Endpoint Readiness Plan

**Endpoint:** `/v2/coupons/apply` (new in v2 API this week)

**Status:** Not battle-tested, unmonitored, unbriefed. Critical blocker for Friday ship unless fully resolved by Thursday 5 PM.

**Success criteria:** Friday launch with live monitoring, briefed support team, updated help-center, and verified error handling.

---

## Overview: Consolidated Risks & Mitigations

The coupon endpoint was flagged by all three roles as a readiness risk:

| Role | Risk | Mitigation |
|------|------|-----------|
| **Engineer** | Schema mismatch w/ production data; untested on real codes/carts | Production data audit + smoke tests |
| **Ops** | No monitoring dashboard; no v2 runbook; silent degradation risk | Dashboard panels + runbook update + alerts |
| **Support** | No briefing on v2 behavior; agents don't know new error messages; help-center stale | 30-min briefing + error code doc + help-center updates |

**These three streams are interdependent:**
- Engineer discovers real error codes during production audit → feeds to Ops dashboard + Support briefing
- Ops builds dashboard using Engineer's error codes → Support references same codes in briefing
- Support briefing covers edge cases from Engineer's audit → Team is synchronized on what "normal" failure looks like

---

## Workstream 1: Engineer — Production Data Audit + Instrumentation

### Owner
Backend engineer who built `/v2/coupons/apply`

### Timeline
- **Tuesday–Wednesday 2026-04-22–23** (while PM is out; parallel with other work)
  - Production data audit: Run 3–4 hours
  - Smoke test definition: 1–2 hours
- **Thursday morning 2026-04-24**
  - Smoke test execution in staging: 2 hours
  - Instrumentation verification in Datadog: 1 hour
  - Error code documentation: 1 hour
- **Thursday 2:00 PM** Deliverable ready for handoff to Ops + Support

### Steps

#### Step 1: Production Data Audit (Tuesday–Wednesday)

Extract a representative sample of real production data to test the new endpoint's assumptions:

1. **Data extraction** (Tuesday evening or Wednesday morning)
   - Query production logs for the last 7 days of coupon codes that were SUCCESSFULLY applied in v1 checkout
   - Extract: coupon code (actual format), user ID, cart total (in cents), discount percentage, restrictions (min cart, specific items)
   - Target: 50–100 real coupon codes across categories (percentage discount, fixed amount, BOGO, free shipping, seasonal codes)
   - Also extract 20–30 FAILED coupon attempts from v1 (codes that didn't apply, with rejection reason)
   - Export as CSV or JSON

2. **Dry-run against staging v2 endpoint** (Wednesday afternoon)
   - Set up a test harness that submits each real coupon code to `/v2/coupons/apply` in staging
   - For each: log the response (success/failure, discount amount, error message if failed)
   - Compare v2 response to expected result:
     - If coupon was successful in v1, v2 should also succeed with same discount
     - If coupon failed in v1 (and should fail), v2 should fail with a reasonable error message
     - Flag any discrepancies: v2 succeeds when v1 failed (overly permissive), or v2 fails when v1 succeeded (regression)

3. **Edge case testing** (Wednesday evening)
   - Test coupon codes with unusual formats discovered in audit (very old codes, codes with special characters, codes near expiry)
   - Test cart edge cases (cart total just below minimum, cart with only restricted items, cart over max discount)
   - Test combinations (stacking multiple coupons if v2 allows)
   - Log any crashes, NULL errors, or unexpected behavior

4. **Summary report** (Thursday 10:00 AM)
   - Document all edge cases discovered
   - List any error messages or validation changes vs. v1
   - Pass/fail: "Coupon endpoint behavior matches v1 for all sampled real data" or "Found N regressions/edge cases requiring fix"
   - If failures found: brief plan to fix before Friday (e.g., "update validation logic," "handle legacy code format")

#### Step 2: Instrumentation (Wednesday–Thursday morning)

Add monitoring metrics to the coupon endpoint so Ops can see performance and errors in real-time:

1. **Instrumentation code** (Wednesday)
   - Add metrics to `/v2/coupons/apply`:
     - `coupon_apply_success_rate` (success / total requests, tagged by code)
     - `coupon_apply_latency` (p50, p95, p99, tagged by code)
     - `coupon_apply_error_count` (tagged by error type: schema_error, code_not_found, code_expired, cart_invalid, etc.)
     - `coupon_apply_cache_hit_rate` (if caching is used)
   - Ensure error types are granular (not just "error," but specific reasons)

2. **Metric verification in staging** (Thursday morning)
   - Deploy instrumented code to staging
   - Run a few test requests against `/v2/coupons/apply`
   - Verify metrics appear in Datadog with correct tags
   - Verify dashboard queries can be built against these metrics

3. **Metric baseline definition** (Thursday 11:00 AM)
   - Based on staging load test or historical v1 data:
     - Expected success rate: [e.g., 98%+]
     - Expected p99 latency: [e.g., <200ms]
     - Expected error rate for each error type
   - Document these baselines for Ops alerts (Section 2)

#### Step 3: Error Code Documentation (Thursday morning)

Engineer documents all possible error responses from `/v2/coupons/apply`:

1. **Error codes and user-facing messages**
   - Create a table: HTTP status, error code (e.g., `COUPON_NOT_FOUND`), user-facing message ("This coupon code is not recognized"), internal log message, what it means, is it expected behavior?
   - Example:
     ```
     HTTP 404, COUPON_NOT_FOUND, "This coupon code is not recognized.", 
     "Coupon lookup returned empty", Code does not exist in DB, Expected.
     
     HTTP 400, COUPON_EXPIRED, "This coupon has expired.", 
     "Coupon expiry check failed", Code's expiry date is in the past, Expected.
     
     HTTP 400, INVALID_CART, "This coupon cannot be applied to your cart.",
     "Cart validation failed: code requires minimum cart total $X",
     User's cart is below the code's minimum, Expected.
     ```

2. **Known edge cases and workarounds**
   - From the production audit, list edge cases discovered (e.g., "Legacy coupon codes from 2024 may fail if they use old format")
   - For each: does it require a fix, or is it expected? If expected, what's the right error message?

3. **v1 vs. v2 behavior differences**
   - Changes from v1 behavior (e.g., v1 applied coupons synchronously; v2 may cache, so there's a delay?)
   - Are there timing differences, validation differences, or error message differences?

4. **Deliverable:** A 1-page document "Coupon Endpoint v2 — Error Codes & Edge Cases" (shared with Ops and Support)

**Thursday 2:00 PM: Engineer deliverables ready for hand-off**
- [ ] Production audit report
- [ ] Smoke test results
- [ ] Error code documentation
- [ ] Metric baselines
- [ ] Updated instrumentation deployed to staging (ready for prod Thursday evening after approval)

---

## Workstream 2: Ops — Dashboard + Runbook + Alerts

### Owner
Ops engineer (checkout team)

### Timeline
- **Thursday morning 2026-04-24** — Receive Engineer's error codes + metrics
- **Thursday 2:00 PM – 4:00 PM** — Build dashboard panels + update runbook
- **Thursday 4:00 PM – 5:00 PM** — Verify dashboard live, runbook ready, alerts tested

### Steps

#### Step 1: Dashboard Panels (Thursday afternoon)

Build Datadog dashboard panels for `/v2/coupons/apply` using Engineer's metrics:

1. **Required panels** (based on Ops pre-mortem):
   - **Panel 1:** Coupon apply success rate (%) over time, with baseline threshold marked (e.g., expected 98%+, alert if <95%)
   - **Panel 2:** Error count by error type (chart showing breakdown: code_not_found, expired, invalid_cart, etc.)
   - **Panel 3:** Latency percentiles (p50, p95, p99) over time, baseline marked (e.g., p99 expected <200ms)
   - **Panel 4:** Cache hit rate (if applicable)
   - **Panel 5:** Request volume by code (to spot anomalies: one code being hit too often, possible abuse)

2. **Dashboard title and grouping:**
   - "V2 Coupon Endpoint — Checkout Launch Monitoring"
   - Group near other v2 checkout metrics (if they exist)
   - Add a description linking to the runbook (see Step 2)

3. **Alert thresholds** (using baselines from Engineer):
   - Success rate < 95% for 2 minutes → page ops-checkout
   - Error count for `code_not_found` > 10 in 5 minutes (possible mass expiry or data issue) → page ops-checkout
   - p99 latency > 500ms for 2 minutes → page ops-checkout (investigate performance degradation)
   - Cache hit rate drops > 20% from baseline → page ops-checkout (investigate cache/dependency issue)

4. **Verification** (Thursday 4:00 PM):
   - Confirm dashboard is live in Datadog
   - Run a few test queries to confirm metrics are visible
   - Share dashboard link with Engineer and Support

#### Step 2: Runbook Update (Thursday afternoon)

Update the checkout on-call runbook to include v2-specific sections:

1. **New section: "V2 Coupon Endpoint — What Changed"**
   - Link to Engineer's error code documentation
   - List the 5 most common error types (from audit) and what they mean operationally
   - Example: "If you see COUPON_NOT_FOUND errors spiking, the code may have been deleted or is outside its valid date range. Check database; if data looks OK, escalate to coupon-service team."

2. **New section: "Monitoring — V2 Coupon Dashboard"**
   - Link to the dashboard panel (from Step 1)
   - Describe what each panel shows and what's normal
   - Example: "Success rate should be >98%. If it drops to <95%, check the dashboard error breakdown: is it all EXPIRED codes (data issue), or is it SCHEMA_ERROR (new code format not handled)?"

3. **New section: "V2 Coupon Troubleshooting Decision Tree"**
   - If coupon endpoint p99 latency is high:
     - Step 1: Check Redis latency (dependency for coupon lookup cache)
     - Step 2: Check coupon database query performance (may need index)
     - Step 3: Check request volume (may need rate limiting)
   - If coupon endpoint error rate is high:
     - Step 1: Check which error type is spiking (use dashboard error breakdown)
     - Step 2: If schema_error, check if malformed requests are hitting the endpoint (security team?)
     - Step 3: If code_not_found, check if codes are being deleted unexpectedly
   - If coupon endpoint is timing out:
     - Step 1: Check coupon service availability (is it up?)
     - Step 2: Check its dependencies (Redis, database)
     - Step 3: Escalate to coupon-service owner

4. **New section: "V2 Rollback Procedure"**
   - Document how to roll back coupon endpoint specifically (if needed)
   - Example: "To disable coupon endpoint and fall back to v1 behavior: (1) flip feature flag `use_v2_coupon_endpoint` OFF, (2) verify v1 coupon flow still works (curl test), (3) monitor support tickets for fallout"

5. **Manual test section:**
   - Add curl examples for v2 coupon endpoint
   - Example: `curl -X POST /v2/coupons/apply -H "idempotency-key: test-123" -d '{"code": "SUMMER2024", "user_id": 12345, "cart_total_cents": 5000}'`
   - Show what success and failure responses look like

6. **Escalation paths:**
   - If coupon endpoint is down or broken, who to page? (coupon-service owner, backend eng?)
   - If it's a data issue (wrong discounts, expired codes), who to page? (data engineer, compliance?)
   - Link to relevant on-call runbooks

#### Step 3: Testing Alerts (Thursday 4:00 PM – 5:00 PM)

Verify that the monitoring is actually set up to trigger:

1. **Dry-run the alert**:
   - Temporarily cause a condition that would trigger the alert (e.g., artificially spike error count in staging)
   - Verify the alert fires and notification reaches ops-checkout Slack channel
   - If it doesn't, troubleshoot (configuration issue, notification routing, etc.)

2. **Document alert response**:
   - Add to runbook: "If you receive an alert for coupon endpoint success rate < 95%, follow this procedure: [link to decision tree above]"

3. **Communicate alert setup to team**:
   - Post in #ops-checkout: "V2 coupon monitoring is live. You'll see alerts on success rate, error spikes, and latency. Dashboard link: [URL]. Runbook: [URL]."

**Thursday 5:00 PM: Ops deliverables ready**
- [ ] Dashboard panels live in Datadog
- [ ] Runbook updated with v2 coupon section
- [ ] Alerts configured and tested
- [ ] Team notified

---

## Workstream 3: Support — Briefing + Documentation

### Owner
Support lead + coupon-endpoint engineer (brief giver)

### Timeline
- **Thursday 10:00 AM** — Receive Engineer's error codes + audit findings
- **Thursday 2:00 PM – 3:00 PM** — 30-minute support briefing
- **Thursday 3:00 PM – 4:30 PM** — Support team updates help-center articles + prepares support guide
- **Thursday 5:00 PM** — All support documentation ready for agent study Friday morning

### Steps

#### Step 1: Support Briefing (Thursday 2:00 PM, 30 minutes)

Engineer + Support team sync on coupon behavior:

**Attendees:**
- Backend engineer who built coupon endpoint (brief giver)
- Support lead
- 2–3 senior support agents (who will train others Friday)
- Optional: Ops engineer (so ops understands the same context)

**Agenda (30 minutes):**
1. **Intro (2 min):** "What changed between v1 coupon and v2 coupon"
2. **Error codes walkthrough (10 min):** Engineer walks through the error codes document — what each error means, what users will see, how support should respond
   - Example: "If a user says 'I got an error: code not found,' they applied a coupon that doesn't exist. It's expected behavior; tell them to double-check the code."
   - Example: "If a user says 'my code won't apply, no error message,' it might be a validation issue we found in testing. Here's how to escalate to us."
3. **Edge cases discovered (8 min):** Engineer presents edge cases from production audit (unusual code formats, cart edge cases, timing issues)
   - What are they? What do users experience? Is it a bug or expected?
4. **Session re-auth behavior (5 min):** Engineer confirms: "If a user says they were logged out mid-checkout, was this a change in v2?" If yes: "Here's the right message to give: 'For security, your session expires after X minutes of inactivity. Your cart is saved; log back in.'"
5. **Q&A + Testing (5 min):** Agents ask clarifying questions; engineer demos a few coupon apply scenarios in staging

**Deliverable from briefing:**
- Agent notes / slide deck on error codes (to share with rest of team Friday)
- Confirmation of session re-auth behavior
- List of edge cases and "expected vs. unexpected" classification

#### Step 2: Support Documentation Updates (Thursday afternoon)

Update internal and external documentation based on briefing + Engineer's error codes:

1. **Internal support guide** (1 page)
   - Title: "Coupon Endpoint v2 — Support Quick Reference"
   - Decision tree: "When user says 'coupon won't apply':"
     - Did they get an error message? If yes: Show error code → reference [error codes table] → respond with suggested message
     - Did they get NO error message? → Likely validation issue → escalate to engineering with details
   - List of known edge cases: "If user applies an old legacy coupon code from 2024, they may see an error. This is expected; suggest they use a current code."
   - Session re-auth FAQ: "Why was I logged out mid-checkout?" → Response script: "For security, we re-authenticate after [X] minutes. Your cart is saved; please log back in."
   - Escalation criteria: "If you see 5+ 'coupon' tickets in 1 hour with the same error code or symptom, post in #ops-escalation with pattern and details."

2. **Help-center articles** (on zendesk.yourco.com or equivalent)
   - **Article 1: "Why didn't my coupon apply?"**
     - Compare against v2 error codes from Engineer's documentation
     - Update error codes and messages to match v2 responses
     - Add examples of each error with recommended user actions
     - Publish by Thursday 4:00 PM
   
   - **Article 2: "Why was I logged out during checkout?"**
     - Clarify whether this is a known v2 behavior change
     - If yes: update with expected behavior and response script
     - Publish by Thursday 4:00 PM
   
   - **Article 3: "Coupon troubleshooting" (if exists)**
     - Audit for any v1-specific references
     - Update troubleshooting steps to align with v2 behavior
   
   - **New article (optional): "What's new in our April 2026 checkout"**
     - High-level overview of changes (new coupon system, session handling, etc.)
     - Link to relevant articles (why coupon didn't apply, session FAQ)
     - Helps with search and user self-service

3. **Agent training notes** (Friday morning)
   - Support lead prepares a 10-minute morning standup briefing Friday:
     - Key points from Thursday's engineer briefing
     - Link to error codes document + internal quick reference
     - Remind of escalation path (#ops-escalation for patterns)
     - Q&A for any overnight questions

#### Step 3: Staffing Plan (Thursday EOD confirmation)

Confirm weekend + Monday staffing:

1. **Weekend (Sat–Sun)** — Normal coverage (2 agents weekend shift)
   - Equip them with error codes guide + help-center updates
   - They should be alert for "coupon" and "session" keyword spikes (early signal)

2. **Monday (100% ramp day)** — Elevated coverage
   - Schedule 4 agents (instead of normal 3) from 7 AM – 2 PM
   - This covers the expected ticket spike from 48–72-hour post-launch pattern + 100% ramp
   - Briefed agents should be on Monday; hold over Friday's brief givers if possible

3. **Escalation readiness**
   - Confirm #ops-escalation Slack channel is created and monitored
   - Escalation script: "If I see 5+ tickets with the same symptom in 1 hour, I post: '[PATTERN] [symptom], [count] in last hour, first ticket link.' Ops responds within 15 min."

**Thursday 5:00 PM: Support deliverables ready**
- [ ] Support briefing completed
- [ ] Internal quick reference guide ready (1 page)
- [ ] Help-center articles updated
- [ ] Training notes prepared for Friday standup
- [ ] Monday staffing confirmed (4 agents 7 AM – 2 PM)
- [ ] Escalation channel and script confirmed

---

## Sync Points: Ensuring All Three Workstreams Are Aligned

### Dependency Graph

```
Engineer: Production audit (Tue–Wed)
    ↓
Engineer: Error codes + baselines (Thu 10 AM)
    ├─→ Ops: Dashboard panels (Thu afternoon)
    ├─→ Support: Briefing (Thu 2 PM)
    └─→ Engineer: Smoke test results (Thu 10 AM)
         ↓
    Ops: Runbook update (using error codes)
    Support: Help-center updates (using error codes)
         ↓
    All: Verification & testing (Thu 4–5 PM)
         ↓
    All: Ready for Friday ship
```

### Handoff Checkpoints

**Thursday 10:00 AM — Engineer → Ops & Support**
- Engineer delivers:
  - Error codes documentation (all possible responses from endpoint)
  - Metric baselines (expected success rate, latency, error types)
  - Production audit findings + edge cases
  - Smoke test results (pass/fail on real-data testing)
- Ops & Support receive and review (30 min)

**Thursday 2:00 PM — Ops & Support Alignment**
- Support briefing happens (Engineer + Support + Ops)
- Ops confirms: "The error codes and edge cases Support is learning about are the same ones I'm building alerts for"
- Any discrepancies are resolved

**Thursday 4:00 PM — Final Verification**
- Ops confirms: Dashboard live, alerts tested, runbook published
- Support confirms: Help-center articles updated, agent training ready
- Engineer confirms: All instrumentation deployed, baselines set
- All three lead: "Ready for Friday ship"

---

## Delivery Checklist: "Coupon Endpoint Ready for Friday Launch"

### Engineer Workstream

- [ ] **Production data audit complete** (Tuesday–Wednesday)
  - Extracted 50–100 real coupon codes and 20–30 failed attempts
  - Tested against v2 endpoint in staging
  - Documented any regressions or edge cases
  - Pass/fail: "All real-data coupon codes behave correctly in v2"

- [ ] **Smoke tests defined and executed** (Thursday)
  - Tests for unusual code formats (legacy codes, special characters, near-expiry)
  - Tests for cart edge cases (below minimum, only restricted items, over max)
  - All tests pass OR documented as known issues with workarounds
  - Pass/fail: "Smoke test results: [count] passed, [count] known issues"

- [ ] **Instrumentation added and verified** (Thursday morning)
  - Metrics added to `/v2/coupons/apply`: success_rate, latency, error_count (by type), cache_hit_rate
  - Metrics visible in Datadog (staging)
  - Pass/fail: "All metrics visible in staging Datadog"

- [ ] **Error code documentation** (Thursday 10 AM)
  - Error codes table with HTTP status, code, user message, internal message, expected/unexpected
  - Known edge cases listed with classifications
  - v1 vs v2 behavior differences documented
  - Pass/fail: "Error code document ready for Ops & Support review"

- [ ] **Metric baselines defined** (Thursday 11 AM)
  - Expected success rate: [X]%
  - Expected p99 latency: [X]ms
  - Expected error type distribution
  - Pass/fail: "Baselines defined and shared with Ops for alerts"

- [ ] **Instrumentation deployed to production** (Thursday evening, after approval)
  - Code changes deployed
  - Metrics flowing to Datadog
  - Pass/fail: "Instrumentation live in production before Friday ship"

**Engineer go/no-go:** Smoke tests pass, no regressions, instrumentation deployed, error codes documented

---

### Ops Workstream

- [ ] **Dashboard panels created** (Thursday afternoon)
  - Panel 1: Success rate (%)
  - Panel 2: Error count breakdown by type
  - Panel 3: Latency percentiles
  - Panel 4: Cache hit rate (if applicable)
  - Panel 5: Request volume by code
  - Pass/fail: "All 5 panels live in Datadog, metrics visible, baselines marked"

- [ ] **Alerts configured and tested** (Thursday 4–5 PM)
  - Alert 1: Success rate < 95% → page ops-checkout
  - Alert 2: Error count of specific type spiking → page ops-checkout
  - Alert 3: p99 latency > 500ms → page ops-checkout
  - Alert 4: Cache hit rate drops > 20% → page ops-checkout
  - Test each alert: trigger condition, verify notification reaches Slack
  - Pass/fail: "All alerts tested and firing correctly"

- [ ] **Runbook updated** (Thursday afternoon)
  - Section: "V2 Coupon Endpoint — What Changed"
  - Section: "Monitoring — V2 Coupon Dashboard" (with link)
  - Section: "V2 Coupon Troubleshooting Decision Tree"
  - Section: "V2 Rollback Procedure"
  - Section: "Manual test examples (curl)"
  - Section: "Escalation paths"
  - Pass/fail: "Runbook published and link shared with Support & Engineer"

- [ ] **Team notified of live monitoring** (Thursday 5 PM)
  - Slack post in #ops-checkout: "V2 coupon monitoring live. Dashboard: [link]. Runbook: [link]. Alerts active."
  - Pass/fail: "Team acknowledgment in Slack or read receipt"

**Ops go/no-go:** Dashboard live, alerts tested, runbook published, team notified

---

### Support Workstream

- [ ] **30-minute briefing completed** (Thursday 2 PM)
  - Attendees: Engineer + Support lead + 2–3 senior agents + (optional) Ops
  - Topics: Error codes, edge cases, session re-auth behavior
  - Deliverable: Notes or slides on error codes for rest of team
  - Pass/fail: "Briefing completed, notes distributed"

- [ ] **Internal quick reference guide** (1 page, Thursday 3 PM)
  - Title: "Coupon Endpoint v2 — Support Quick Reference"
  - Decision tree: "When user says 'coupon won't apply'"
  - Known edge cases
  - Session re-auth FAQ + response script
  - Escalation criteria
  - Pass/fail: "Guide ready and shared with all agents"

- [ ] **Help-center articles updated** (Thursday 4 PM)
  - Article: "Why didn't my coupon apply?" — updated with v2 error codes
  - Article: "Why was I logged out during checkout?" — clarified v2 behavior
  - Article: "Coupon troubleshooting" — audited for v1 references and updated
  - Article: (optional) "What's new in April 2026 checkout"
  - Pass/fail: "Articles live on help center, tested with sample scenarios"

- [ ] **Agent training notes prepared** (Thursday 5 PM)
  - 10-minute Friday morning standup briefing
  - Key points from Engineer briefing + links to guides
  - Escalation script reminder
  - Pass/fail: "Notes ready for Friday standup"

- [ ] **Monday staffing confirmed** (Thursday EOD)
  - Weekend coverage: 2 agents, equipped with guides
  - Monday 7 AM – 2 PM: 4 agents (elevated for ramp spike)
  - Briefed agents scheduled for Monday if possible
  - Pass/fail: "Staffing plan confirmed, agents notified"

- [ ] **Escalation channel and script ready** (Thursday EOD)
  - #ops-escalation channel created and monitored
  - Agents briefed: "If 5+ similar tickets in 1 hour, post '[PATTERN]' message"
  - Ops briefed: "Monitor #ops-escalation and triage within 15 min"
  - Pass/fail: "Channel live, script documented and acknowledged by ops + support"

**Support go/no-go:** Briefing done, help-center updated, agents trained, Monday staffing confirmed, escalation channel active

---

## Final Sync: Thursday 5 PM

**All three lead** (Engineer, Ops, Support) meet for 15 minutes:

1. **Engineer:** "Production audit passed. Instrumentation deployed. Error codes documented."
2. **Ops:** "Dashboard live, alerts tested, runbook published."
3. **Support:** "Agents briefed, help-center updated, Monday staffing confirmed."
4. **Exec decision:** Ship Friday? Yes/No

If all three are go → **Friday ship is green on coupon endpoint.**

If any is no-go → **Escalate to PM/eng lead for decision.**

---

## Success Metrics (Post-Friday Launch)

To validate the plan worked:

- **Friday night–Monday AM:**
  - Ops dashboard shows 0 alerts (or only expected baseline noise)
  - Support team reports no questions about coupon error codes (means briefing was effective)
  - Help-center articles on "coupon" and "session" see normal search traffic (no frustrated users searching for explanations)

- **Monday during 100% ramp:**
  - If coupon endpoint has an issue, Ops detects it via dashboard alert (not via support-ticket spike)
  - Support team escalates via #ops-escalation with clear pattern; Ops responds within 15 minutes
  - No "Why didn't anyone tell us?" or "I didn't know what this error meant"

- **Post-launch retro:**
  - Coupon endpoint uptime: 99%+
  - Zero unplanned rollbacks due to coupon issues
  - Support satisfaction with briefing: rated 4+ / 5

---

## Appendix: Risk Mitigation Mapping

| Pre-mortem Risk | Root Cause | Mitigation | Owner | Verified By |
|---|---|---|---|---|
| Schema mismatch on production data | Endpoint untested on real data | Production audit + smoke tests | Engineer | Thursday 10 AM: audit report + test results |
| Ops can't see degradation | No monitoring dashboard | Dashboard panels + alerts | Ops | Thursday 4 PM: dashboard live + alerts tested |
| On-call doesn't know how to respond | No v2 runbook | Runbook update + troubleshooting tree | Ops | Thursday 5 PM: runbook published |
| Support doesn't know behavior | No briefing on v2 changes | 30-min briefing + error code doc | Support + Engineer | Thursday 2 PM: briefing completed |
| Help-center sends users wrong advice | Articles describe v1 behavior | Help-center updates + audit | Support | Thursday 4 PM: articles live |
| Support overwhelmed Sunday/Monday | Unexpected spike + thin weekend coverage | 4-agent Monday coverage + escalation script | Support | Friday morning: staffing confirmed |
| Silent degradation pattern | No early alert for patterns | Escalation script + ops monitoring | Support + Ops | Thursday EOD: script live, ops monitoring active |

---

## Sign-Off

Once all three workstreams are complete and verified, this document serves as proof that the coupon endpoint is ready for Friday launch:

- **Engineer sign-off:** _____________________ (Date / Time)
- **Ops sign-off:** _____________________ (Date / Time)
- **Support sign-off:** _____________________ (Date / Time)
- **PM/Leadership decision:** SHIP / NO-SHIP (Date / Time)
