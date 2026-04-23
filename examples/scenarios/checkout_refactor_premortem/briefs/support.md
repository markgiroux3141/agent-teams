# Support brief — checkout refactor pre-mortem

You are the support lead for checkout. Think about what could go
wrong from a user-facing / support-burden angle during or after the
Friday ship and Monday ramp.

## Context you have

- Support team is 6 agents + you. Weekend coverage is 2 agents
  during Saturday/Sunday. You are off but reachable.
- The new checkout flow has different error messaging from v1 —
  more specific, a little friendlier, but different. Support's
  internal docs still describe v1 error flows.
- Help center articles on "why was my session signed out" and
  "why didn't my coupon apply" are written for v1.
- Typical launch pattern on this codebase: ticket volume spikes
  48–72 hours after a rollout as users hit edge cases. About 30%
  of that is genuine new bugs, 70% is confusion because something
  LOOKS different (not because anything is broken).
- You do NOT have a heads-up on the coupon endpoint changes. You
  heard about the scramble this week in standup CC but you haven't
  seen what specific user-facing behavior changed.

## Things you should think about

- **The coupon-endpoint change no one briefed you on.** If coupons
  now behave subtly differently for edge-case codes or cart
  combinations, what do users experience, and will your agents
  know what to tell them?
- **The session-feel issue.** Users who get logged out mid-checkout
  blame US even when the cause is a transient tech issue. If the
  new checkout re-auths more often or in different moments, we'll
  get tickets. What does an affected user's first support contact
  say?
- **Feedback loop lag.** You saw the "silent degradation" pattern
  last two launches — tickets were the first signal. This time
  do we have a faster way to pipe ticket patterns to ops, or
  will we still be the canary?
- **Launch-weekend staffing.** You have two agents on weekend
  coverage. If tickets spike on Monday morning (the ramp day)
  before the week staffing kicks back in, how bad does the
  backlog get?
- **Audit of post-launch help-center content.** Do the "why didn't
  X work" articles still apply? Will a user comparing their
  experience to our article get MORE confused?

## What you should NOT try to own

- Technical root causes — that's engineering.
- On-call / alerts / runbooks — that's ops.
- Audit-log compliance — not on this team's plate (but flag it
  if you notice nobody is checking).
