# Project context — Checkout refactor

**Today:** Wednesday, 2026-04-22. Day 3 of 5. Ships Friday 2026-04-24.

**Goal:** Cut over the checkout flow from the legacy monolith to the new
payments API v2 + new React checkout. Feature-flagged rollout, ramp to
100% Monday if metrics hold.

**Team:** backend, frontend, qa. PM is out sick until Thursday.

**Recent history:**
- Mon 04-20: backend merged payments API v2 to `main`. Staging deploy
  same day.
- Tue 04-21: frontend started wiring the new checkout screen against v2.
- Tue 04-21: QA began updating the regression suite for the new flow.

**Known open questions as of yesterday EOD:**
- Coupon endpoint shape (nobody has confirmed it matches the mock
  frontend built against last sprint).
- Whether launch is a full cutover or behind a flag. Eng lead said
  "flag it" in Slack last week; release plan doc still says "cutover".
- Staging DB seed data. Something broke when the v2 migration ran; QA
  noticed tests failing Tuesday afternoon but didn't track who owns
  the seed script.

**Launch constraints:**
- Payments team's legacy API goes read-only Saturday.
- Compliance needs a clean audit log for all transactions from Monday
  onward.
