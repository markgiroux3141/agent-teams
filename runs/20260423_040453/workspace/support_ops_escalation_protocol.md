# Support→Ops Escalation Protocol — Checkout v2 Launch

## Overview

The pre-mortem identified a critical "silent degradation" pattern from past launches: support tickets are the first signal that customers are affected (20–60 minutes before monitoring alerts fire). Without a tight escalation protocol, ops stays unaware while customer pain accumulates.

**This protocol establishes support as the CANARY signal for ops.** When support detects a pattern, ops responds immediately.

**Timeline:** Protocol is live Friday 2026-04-24 at ship time. Support and ops are fully briefed by Friday morning.

---

## Escalation Threshold

### When to Escalate

**Pattern Detection:** 5 or more tickets with the same keyword/symptom arrive within a 1-hour window.

**Keywords to Monitor** (team is responsible for tracking):
- Checkout flow: "checkout," "checkout broken," "checkout slow," "stuck on checkout"
- Coupon-related: "coupon," "code," "discount," "coupon didn't apply," "code won't work," "discount not applied"
- Session/auth: "logged out," "signed out," "session expired," "session," "signed me out," "kicked off," "signed out unexpectedly"
- Payment: "payment failed," "payment declined," "payment error," "payment won't process," "card declined"
- Error/timeout: "timeout," "error," "something went wrong," "page didn't load," "stopped responding"

**Escalation Decision Rules:**
- **5+ tickets in 60 min with same keyword** → Escalate immediately (don't wait for 6th ticket)
- **3 tickets in 30 min with same keyword** → Monitor closely, escalate if reaches 5 within next 30 min
- **1–2 tickets in 60 min** → Track in team notes, do NOT escalate yet

**Trend Matters:**
- If ticket rate is rising (2 in first 30 min, then 3 more in next 30 min) → escalate at 5-total threshold
- If ticket rate is stable (1–2 per hour) → NOT a pattern yet, continue tracking

---

## Escalation Channels

### Primary Channel: #ops-escalation

**Audience:** ops-primary (me), ops-secondary (backend engineer), PM (optional), lead (CC'd by system)

**When to use:** Monday morning ramp, anytime during business hours, any time you hit the 5-ticket threshold.

**Monitoring SLA:** Ops checks #ops-escalation every 15 minutes during waking hours (Friday 16:00 UTC onwards). Response target: 5 minutes for acknowledgment, 15 minutes for triage.

**Format (required):**
```
[PATTERN] <keyword>
Symptom: <what users are reporting>
Count: <N> tickets in last 60 min
First ticket: <timestamp> 
Most recent: <timestamp>
Trend: [rising / stable / falling]
Attached: <3 example tickets with exact error messages or user quotes>
```

**Example:**
```
[PATTERN] coupon not applying
Symptom: Users say "coupon code didn't apply" or "discount not showing on checkout"
Count: 6 tickets in last 45 min
First ticket: 2026-04-27 10:15 UTC
Most recent: 2026-04-27 11:00 UTC
Trend: rising (1 ticket at 10:15, then 2 at 10:30, then 3 at 10:45)
Attached: 
- Ticket #S-1234: "Applied promo code SPRING20, says it's valid, but no discount appears. Error: 'code applied' but cart total unchanged."
- Ticket #S-1235: "Code SPRING20 worked yesterday, now it won't apply. Same error."
- Ticket #S-1236: "Tried SPRING20 and SUMMER10, neither shows discount. Both say 'applied' but nothing changes."
```

### Secondary Channel: #checkout-launch-ops (Bridge channel for weekend)

**Audience:** support team, ops-primary, ops-secondary, PM (optional)

**When to use:** Friday evening → Monday morning (thin crew hours). Real-time coordination channel. Lower barrier for casual escalation, higher frequency monitoring.

**Monitoring SLA:** Ops checks every 15–30 minutes during off-hours. Posts in this channel count toward the escalation SLA (ops will acknowledge in same channel within 5 minutes of seeing message).

**Format (informal, conversational):**
```
@channel or @ops-primary: [brief issue description]
Count: N tickets in last [X] min
Keywords: [list of recurring terms]
Support's assessment: [what does support think is happening?]
```

**Example:**
```
@ops-primary: Seeing uptick in session errors. 4 tickets in last 30 min, all saying they got logged out mid-checkout and cart was cleared.
Keywords: "logged out," "lost cart," "session expired"
Support: Looks like session store might be unstable or timeout is shorter. Not seeing this much in baseline.
```

### Urgent Escalation (not the threshold, but critical)

**If ticket rate is >5 tickets per 30 minutes (very rapid spike):**
- Escalate to #ops-escalation AND mention @ops-primary in Slack (but do NOT page yet)
- Format: "[URGENT-PATTERN] keyword. Spike rate: [N] tickets in 30 min. Escalating to ops for immediate triage."

**If tickets mention data loss, billing errors, or account compromise:**
- Escalate to #ops-escalation immediately (do not wait for 5-ticket threshold)
- Format: "[DATA-ISSUE] keyword. [description]. Escalating to ops and compliance."

---

## Ops Response Procedure

### Minute 0–5: Acknowledge and Validate

1. **Acknowledge** in #ops-escalation (or #checkout-launch-ops): "Received [keyword] escalation. Checking dashboard and logs."
2. **Validate** the pattern:
   - Open ramp_metrics_plan.md dashboard (Datadog `Checkout v2 Ramp — Metrics Comparison`)
   - Check if v2 error rate, latency, or specific endpoint (e.g., coupon) is elevated
   - Check system/application logs for error spikes in the same window (log entries matching keyword)
   - Determine: Is this a real issue (system degradation) or a false positive (normal variation, user confusion)?

### Minute 5–10: Categorize the Issue

**Category A: Real Issue (confirmed by metrics)**
- Metrics show v2 degradation (error rate spike, latency spike, or endpoint-specific issue)
- Example: coupon endpoint error rate jumped from 0.5% to 5%, tickets match
- **Action:** Post in channel: "Confirmed issue. [metric] shows degradation. Paging engineer for investigation. ETA: 10 min."

**Category B: Possible Issue (metrics are ambiguous)**
- Metrics don't clearly confirm or deny (could be noise, could be real)
- Example: overall error rate is stable, but coupon tickets are arriving (coupon endpoint alert hasn't fired yet)
- **Action:** Post in channel: "Metrics inconclusive. [diagnosis]. Escalating to engineer for deeper investigation. Checking logs for patterns. Will update in 10 min."

**Category C: False Positive (metrics are normal)**
- Dashboard shows v2 metrics are healthy, no corresponding alert fired
- Tickets are isolated (not correlated with each other, different error messages, different coupons/users)
- Example: 5 different users, 5 different coupons, all say "code didn't work," but coupon endpoint error rate is 0.2% (normal)
- **Action:** Post in channel: "No degradation detected in metrics. [diagnosis: likely user error / known limitation]. Support response: [what should support tell customer?]."

### Minute 10–15: Escalate or Resolve

**If Category A (real issue):**
- Page engineer on-call: "Checkout v2 issue confirmed: [keyword] tickets correlate with [metric] degradation. See #ops-escalation for details."
- DM engineer the dashboard link + the 3 example tickets
- Post in #ops-escalation: "Paged engineer. Issue: [brief]. Impact estimate: [N] users affected based on ticket volume. Investigating."
- Follow up every 5 minutes with status updates until engineer responds

**If Category B (ambiguous):**
- Post in #ops-escalation: "Escalating to engineer for deeper look. Metrics are borderline; checking application logs / traces for the specific symptom."
- Message engineer (not a page yet, but a heads-up): "Support escalated [keyword] tickets (N in 1 hour). Metrics don't clearly confirm or deny. I'm checking logs. Will page if pattern is confirmed."
- Commit to update support within 10 minutes with either: "This is a real issue, paging team" or "This is likely [known issue / user behavior], support should respond with [specific guidance]."

**If Category C (false positive):**
- Post in #ops-escalation: "No issue detected. [Diagnosis]. Support, please respond to tickets with: [suggested response template]."
- Example response template: "We checked our systems and didn't see an issue during that time. This coupon code should work. Try clearing your browser cache and re-entering the code. If it still doesn't work, reply here with the exact code and we'll look into it."
- Update support's ticket knowledge base with the diagnosis (e.g., "Coupon code validation is case-sensitive" or "Coupons from previous year are no longer valid")

---

## Ops Secondary (Backend Engineer) Procedure

**You are ops-secondary on-call Friday night through Sunday.** If ops-primary is unreachable or delayed, you are responsible for escalation.

### When #ops-escalation Goes Unanswered (>5 min)

1. Check #ops-escalation for the escalation message
2. Assess urgency:
   - If >5 tickets in 30 min (very rapid): This is urgent
   - If 5 tickets in 60 min (normal threshold): Moderate urgency
   - If earlier in ramp window (Friday evening, lower traffic expected): Moderate urgency
3. **Try to reach ops-primary:**
   - Slack DM with "hey, support escalated [keyword]. See #ops-escalation."
   - Wait 2 minutes
4. **If ops-primary doesn't respond:**
   - Post in #checkout-launch-ops: "@ops-primary not responding. I'm escalating. Support flagged [keyword] pattern. Checking if it's a real issue."
   - Do **NOT** page engineer yet (you are not ops, you don't have authority to page for customer issues)
   - Instead, check the metrics yourself in Datadog:
     - Is v2 error rate elevated? (check ramp_metrics_plan.md dashboard)
     - Is there a log spike matching the keyword?
   - Post your assessment in #checkout-launch-ops: "Metrics check: [diagnosis]. Ops-primary should respond / escalate."
   - If it looks like a real issue (metrics confirm), DM ops-primary's manager: "Ops-primary unreachable, support escalation waiting. Issue looks real. Advising ops-primary to check #checkout-launch-ops."

### When You See an Escalation in #checkout-launch-ops

This is the informal bridge channel. You should:
1. Acknowledge quickly: "Got it. Checking."
2. Pull up the metrics (same as ops-primary would do)
3. Post your assessment: "Metrics show [diagnosis]. Likely [real issue / false positive / data inconclusive]."
4. If it looks real: escalate to ops-primary or to engineer (your call, based on how urgent it is)

---

## Support Team: Pre-Launch Briefing Agenda (Friday morning, 30 min)

**Lead:** Ops-primary  
**Attendees:** All 6 support agents (including weekend staff), support lead, ops-secondary  
**Timing:** Friday 14:00 UTC (2 hours before ship)

### Agenda

1. **The "silent degradation" pattern (5 min)**
   - Explain: In past launches, support tickets arrived 20–60 min before ops noticed via alerts
   - Why: Support handles real users; monitoring is sometimes slow to alert
   - Impact: If support doesn't escalate quickly, ops stays in the dark while customer pain accumulates
   - Goal: Make support the early-signal system ops relies on

2. **The escalation threshold and channel (5 min)**
   - Threshold: 5+ tickets with same keyword in 1 hour
   - Channel: #ops-escalation (primary) or #checkout-launch-ops (bridge, weekend)
   - Format: "[PATTERN] keyword, N tickets in last 60 min, first 3 tickets attached"
   - Response SLA: Ops will acknowledge within 5 min, triage within 15 min

3. **Keywords to monitor (5 min)**
   - Show the keyword list (coupon, session, payment, error, timeout, etc.)
   - Emphasize: You don't have to understand the technical issue. Just recognize the pattern (5+ same words).
   - Tools: Use Zendesk or your ticket system to filter by keyword and count tickets in the last hour

4. **What to include in an escalation (5 min)**
   - Symptom (what users are reporting in their own words)
   - Count (N tickets in last X min)
   - Timestamps (when first and most recent arrived)
   - Trend (is it growing, stable, or falling?)
   - First 3 example tickets (copy-paste the exact user message or error they saw)

5. **Weekend-specific procedure (5 min)**
   - Friday evening through Monday: ops-primary is on-call (that's me)
   - If you don't get a response in #ops-escalation within 10 min, also post in #checkout-launch-ops (informal channel)
   - We will be monitoring both channels closely

6. **What NOT to do (3 min)**
   - Do NOT wait for ops to ask you about a pattern. You escalate.
   - Do NOT combine different issues into one escalation (keep patterns separate)
   - Do NOT speculate about root cause ("I think it's a database issue"). Just report the pattern.
   - Do NOT wait for the 6th ticket. Escalate at 5.

7. **Q&A and drill (2 min)**
   - Run a 30-second drill: "You get ticket #1 about coupon not applying at 10:00 UTC. At 10:15, you get ticket #2 and #3 with the same issue. By 10:30, you have 5 tickets. What do you do?" (Answer: Post to #ops-escalation with the pattern)

### Pre-Launch Support Readiness Checklist
- [ ] All support agents and weekend staff have attended the briefing
- [ ] #ops-escalation channel is created and support team has access
- [ ] #checkout-launch-ops channel is created and support team has access
- [ ] Keyword list is printed/shared in support Slack or ticket tool
- [ ] Support team knows how to filter tickets by keyword in their tool (Zendesk search tips)
- [ ] Support team has a template for escalation message saved
- [ ] Ops-primary contact info (Slack DM, phone) is posted in #checkout-launch-ops
- [ ] Support team understands they will get a response within 15 min from ops

---

## Ops Secondary (Backend Engineer): Pre-Launch Briefing (Friday morning, 10 min)

**Lead:** Ops-primary  
**Attendees:** Ops-secondary (engineer on-call), ops-primary  
**Timing:** Friday 13:00 UTC (3 hours before ship), or async Slack message

### Key Points

1. You are the ops secondary on-call Friday evening through Sunday
2. If support escalates a [PATTERN] message and ops-primary doesn't respond within 5 min, you should:
   - Check #ops-escalation for the message
   - Do a quick metric check (see the ramp_metrics_plan.md dashboard)
   - Either page ops-primary if it looks urgent, or post in #checkout-launch-ops for ops-primary to see
3. Do NOT assume ops-primary is asleep. They might be investigating another issue. Give them 5 min.
4. Do NOT page engineer on-call for a support escalation (that's ops-primary's call). Your role is to unblock ops-primary.
5. The goal: ensure support escalations don't go unanswered for hours

---

## Ops Primary (Me): Weekend Monitoring and Response Commitment

**Friday 16:00 UTC (ship time) through Monday 18:00 UTC (end of Monday ramp):**

- **Monitor #ops-escalation** every 15 minutes (set phone alarm for 15-min intervals if you're sleeping nearby)
- **Monitor #checkout-launch-ops** every 30 minutes during off-hours
- **Response target:** Acknowledge any escalation within 5 minutes, triage within 15 minutes
- **Decision:** By minute 15, post one of three conclusions:
  1. "Confirmed issue. Paging engineer." (Category A)
  2. "Metrics ambiguous. Escalating to engineer for deep look." (Category B)
  3. "No degradation detected. Support response template: [X]" (Category C)
- **Follow-up:** If issue is paged to engineer, update #ops-escalation every 5 minutes with status

---

## Pre-Launch Checklist (Ops)

- [ ] #ops-escalation Slack channel created and support + ops + PM have access
- [ ] #checkout-launch-ops Slack channel created and support + ops + engineer + PM have access
- [ ] Pinned message in #ops-escalation with link to ramp_metrics_plan.md dashboard
- [ ] Keyword list finalized and shared with support team
- [ ] Support briefing scheduled for Friday 14:00 UTC, invites sent
- [ ] Ops-secondary briefing scheduled for Friday 13:00 UTC (or async Slack message ready)
- [ ] Response template for Category C false positives drafted (e.g., "Clear browser cache and try again")
- [ ] Phone alarm set for 15-min check-ins Friday night and Saturday/Sunday
- [ ] Datadog dashboard bookmarked and tested (can pull it up in <10 seconds)
- [ ] Alerting for Slack notifications configured (so you don't miss an escalation even if not actively watching)

---

## Expected Improvements

### Current State (Before Protocol)
- Support sees tickets arriving at 10:15, 10:30, 10:45 UTC (coupon issue)
- Support spends 30 min determining it's a pattern
- Support pings Slack at 11:00 UTC: "hey, we're seeing coupons not working"
- Ops sees message at 11:15 UTC (off-hours, slower response)
- Ops spends 15 min checking dashboard and calling engineer
- Engineer is paged at 11:30 UTC
- User impact: ~30–45 minutes from first ticket to ops notice

### Future State (With Protocol)
- Support sees tickets arriving at 10:15, 10:30, 10:45 UTC
- Support recognizes pattern at 10:45 (3 tickets, counting more likely to hit 5)
- Support escalates to #ops-escalation at 10:55 UTC (ahead of the 5-ticket threshold): "[PATTERN] coupon, trending up"
- Ops sees message at 10:58 UTC (checking regularly during launch)
- Ops checks dashboard, confirms coupon endpoint degradation at 11:00 UTC
- Ops pages engineer at 11:02 UTC with full context
- Engineer starts investigation at 11:05 UTC
- User impact: ~5–10 minutes from first ticket to ops notice (80% improvement)

---

## Feedback and Iteration

After Monday ramp completes, ops + support lead will meet to review:
- How many escalations came in? (expected: 1–3 patterns during 4-day window)
- Were they actionable? (did they correspond to real issues?)
- Were there false positives? (did ops spend time on non-issues?)
- Did the 15-min SLA hold? (did ops respond within 15 min?)
- Should the threshold change for future launches? (5+ tickets felt right, or adjust?)

Document findings in launch retro.
