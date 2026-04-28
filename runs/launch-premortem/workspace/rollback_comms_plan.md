# Rollback Communications Plan — Checkout Refactor Launch

**Status:** Ready for activation Friday–Monday if rollback is triggered.

**Ownership:** Support Lead (you) owns the plan and decides when to activate. Ops triggers the actual rollback. Support Comms Team executes the notifications.

---

## When This Plan Activates

Rollback messaging is triggered if:
- Ops decides to roll back the feature flag during ramp (Friday–Monday)
- Multiple support tickets surface a common failure pattern (coupon apply, session/auth, payment processing)
- Ops indicates "rollback in progress" in #ops-checkout or to the support lead directly

**Do not wait for ops to ask for comms.** Support lead monitors ticket patterns and proactively reaches out to ops if you see a spike matching one of the known risks (see below).

---

## Known Failure Scenarios & Early Signals

Based on engineering and ops risk assessment, the most likely rollback triggers are:

1. **Coupon endpoint schema mismatch** — User sees "coupon code didn't apply" or "invalid code" errors, even for codes that worked in v1. Early signal: 5+ "coupon" + "error"/"invalid"/"didn't apply" tickets within 1 hour on Monday morning.

2. **Session/auth timeouts under ramp load** — User gets "session expired" or "please log in again" mid-checkout. Early signal: 5+ "session"/"logged out"/"timed out" tickets within 1 hour.

3. **Payment processing failures** — User sees "payment method not found" or generic checkout timeout (>5 seconds). Early signal: 5+ "payment"/"declined"/"error" tickets within 1 hour.

4. **Duplicate charge risk** — Idempotency gaps during ramp or rollback. User may have been charged twice if they retried payment. Early signal: Support gets calls asking "was I charged twice?" or "why do I have two pending charges?"

**If you see any of these patterns Monday 7 AM – 2 PM, immediately escalate to ops:**
- Ping #ops-checkout: "Pattern detected: [keyword], [N] tickets in [time window]. Possible rollback trigger?"
- If ops is unavailable, page ops-primary.
- Do not assume ops has seen the pattern in their dashboards; you'll see customer complaints first.

---

## Notification Audience & Segmentation

### Tier 1: Directly Affected Users (send immediately after rollback)
**Who:** Users who attempted checkout during the affected time window (e.g., Friday 5 PM – Monday 2 PM if rollback at 2:15 PM Monday).

**How identified:** Export checkout sessions from the feature-flagged v2 checkout (ops or eng provides this list). Segment by:
- Users who reached the payment step (highest risk of confusion)
- Users who received an error during checkout
- Users who received an error AND retried (highest risk of duplicate charge concern)

**Notification method:** Email, in-app notification (if they log in), and support team outreach (ops provides phone numbers if enterprise).

**Timeline:** Send within 30 minutes of rollback completion so affected users aren't left wondering if their order went through.

---

### Tier 2: All Users (send within 4 hours of rollback)
**Who:** All users. Broad announcement to prevent confusion and manage perception.

**Notification method:** In-app notification (banner or pop-up), email, status page update.

**Timeline:** 1–4 hours after rollback, once you have stable messaging and FAQ ready.

---

## Tier 1 Message (Directly Affected Users)

**Subject line:** "We paused our new checkout experience — here's what happened"

**Body:**

---

Hi [Name or generic "there"],

We temporarily rolled back our new checkout experience between Friday and Monday. If you attempted to check out during this time, here's what you need to know.

**What happened?**
After launching our redesigned checkout on Friday, we encountered an issue during Monday's traffic ramp that affected checkout reliability. Out of caution, we rolled back to our previous checkout experience to protect your transactions and data.

**Did my order go through?**
- **If you saw an error message:** Your payment was NOT processed. Your payment method was not charged.
- **If you completed checkout without an error:** Your order went through normally and is being prepared.

**Will I be charged twice?**
No. We have reviewed all transactions from the affected window. If you retried payment after seeing an error, we have safety measures in place to prevent duplicate charges. Your card will only be charged once for each completed order.

**What do I do next?**
- **Your order status:** Check your account or your order confirmation email. If you don't see a confirmation, the order did not complete.
- **Missing or failed order:** You can retry checkout now — we've rolled back to our previous checkout experience, which is fully tested and stable.
- **You were charged but didn't get a confirmation:** Please reply to this email or contact support immediately. We'll investigate and refund you if needed.

**Questions?**
Our support team is standing by. Reply to this email, visit our help center at [link], or call [number] (available 24/7 through Monday).

We're sorry for the inconvenience. We'll be running additional testing before we try the new checkout again.

Thank you,
[Company] Support Team

---

---

## Tier 2 Message (All Users)

**Subject line:** "Update: our checkout experience has been temporarily rolled back"

**Body:**

---

We've temporarily rolled back our new checkout experience to our previous version while we investigate some issues encountered during Monday's launch.

**What happened?**
We released a redesigned checkout experience on Friday and ramped it up gradually through Monday. We encountered some issues during Monday morning and decided to roll back to our previous, well-tested checkout to protect your transactions.

**Will this affect me?**
- **If you checked out before Monday morning:** No change. Your orders are fine.
- **If you tried to check out Monday morning and saw an error:** Your payment was not processed. You can retry now using our previous checkout.
- **If you checked out successfully Monday morning:** No change. Your order is being prepared.

**What's next?**
We're investigating what went wrong and will improve our testing before releasing the new checkout again. We'll share an update later this week.

Thank you for your patience.

[Company] Support Team

---

---

## Support FAQ (for support agents to use during rollback)

### Q: Did my payment go through?
**A:** Check your order confirmation email. If you don't see a confirmation, the order did not complete. If you are unsure, reply to the rollback notification email or contact us and we'll check for you.

### Q: Why didn't my coupon code apply?
**A:** Our new checkout was rolled back during Monday morning due to an issue with how coupon codes were processed. You can retry your purchase now with your coupon code — it will work with our previous checkout.

### Q: Why was I logged out mid-checkout?
**A:** This was one of the issues we encountered during the new checkout rollout. It has been resolved. Try checking out again.

### Q: I think I was charged twice. What do I do?
**A:** This is a priority. Reply to the rollback notification, call support at [number], or email [support email]. We will verify your charges and refund any duplicate charges within 24 hours.

### Q: When will the new checkout come back?
**A:** We're running more testing first. We'll announce a new timeline later this week.

### Q: I have a different issue / I'm still seeing an error after rollback.
**A:** Contact us immediately. We've rolled back to our previous checkout, which is fully tested. If you're still seeing an error, it may be a different issue and we want to resolve it right away.

---

---

## Escalation Workflow & Roles

### If Rollback Happens (Monday during ramp, 7 AM – 2 PM):

**1. Support Lead (you)** — Monitors ticket patterns
- Watch for spike in keywords: "coupon," "session," "logged out," "payment," "error," "timed out," "declined"
- If 5+ tickets with same keyword in 1 hour, escalate immediately to ops (ping #ops-checkout, page ops-primary if needed)
- Do not assume ops has seen it in dashboards — you see complaints first

**2. Ops** — Decides rollback
- Evaluates whether the issue is rollback-worthy or fixable in-place
- Executes rollback (changes feature flag to 0%)
- Notifies support lead: "Rollback complete at [time]"
- Provides ops with:
  - List of affected user IDs / sessions (for Tier 1 email segmentation)
  - Brief explanation of what went wrong (for support FAQ/FAQ refinement)

**3. Support Lead** — Confirms readiness & activates comms
- Upon ops notification of rollback completion, immediately:
  - Update FAQ with ops' explanation (if new details)
  - Brief support team on what happened + FAQ answers
  - Send Tier 1 notification to affected users (support comms team executes, support lead approves copy)

**4. Support Comms Team** — Executes all notifications
- Compiles affected user list from ops
- Sends Tier 1 email to affected users (within 30 min of rollback)
- Sends Tier 2 broadcast to all users (within 1–4 hours of rollback, after FAQ is finalized)
- Updates status page
- Monitors replies and escalates urgent issues (double-charges, missing orders) to support lead

**5. Engineering** — Available for urgent questions
- Clarifies what the issue was for support FAQ
- Available to dig into specific user transactions if duplicate-charge refund is needed

---

## Pre-Friday Checklist (Ready by EOD Thursday)

- [ ] Rollback notifications (Tier 1 & Tier 2) drafted and approved by support lead
- [ ] Support FAQ reviewed by support lead and eng
- [ ] Escalation workflow shared with ops, eng, and support team
- [ ] Support Comms Team trained on notification process
- [ ] Email template and in-app notification copy locked (template ready in email client / in-app system)
- [ ] Ops provides process for getting affected user list post-rollback (e.g., query exports, CSV)
- [ ] Support lead shares this plan with ops and eng leads

---

## Post-Rollback (Monday evening)

- [ ] Tier 1 notifications sent within 30 minutes of rollback
- [ ] Tier 2 notifications sent within 1–4 hours
- [ ] Support FAQ refined based on ops' explanation of the issue
- [ ] All replies to rollback notifications monitored for escalations
- [ ] Support lead drafts a public blog post / announcement for Wednesday (after PM returns) explaining what happened, what we learned, next steps
- [ ] Support team monitors for patterns in customer replies (complaints, refund requests) and escalates clusters to ops/eng for investigation

---

## Notes & Contingencies

**If there's ambiguity about whether rollback is needed:**
- Support lead and ops lead do a brief call (5 min) to align on severity
- Ops shows support lead the dashboards (error rates, latency, business impact)
- Support lead shares customer-complaint patterns
- Together decide: roll back now, roll back after ramp completes, or fix in-place

**If rollback happens Friday (before ramp):**
- Same process, but Tier 1 audience is much smaller (only users on feature flag)
- Tier 2 message emphasizes we caught it early

**If a user has a refund request or duplicate-charge claim post-rollback:**
- Support escalates to support lead
- Support lead confirms with ops/eng whether it's a known issue
- If known issue: auto-approve refund (support comms team executes within 24 hours)
- If isolated issue: eng investigates transaction logs and confirms with support lead

**If there's urgency from a high-value customer:**
- Support lead is the point of escalation; support lead reaches out to ops/eng for priority investigation

---

## Version History

- **v1** (2026-04-23): Initial draft, ready for Friday launch.

