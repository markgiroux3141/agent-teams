# Pre-mortem context — Checkout refactor launch

**Today:** Tuesday 2026-04-21. Two days before Friday's planned ship
of the checkout refactor (payments API v2 + new React checkout flow,
feature-flagged rollout ramping to 100% Monday if metrics hold).

**The pre-mortem prompt (imagined failure):**

> It is now Monday 2026-04-27, the day after the 100% ramp.
> The launch went badly. Something about the cutover has caused
> enough pain that we are discussing rollback.
>
> **WHY?** What happened? What did we fail to see coming?

Each contributor imagines this failure state from their angle and
surfaces 3–5 failure modes that could plausibly get us there. The
lead (PM/facilitator) will then cluster duplicates, flag gaps where
no role has natural ownership, re-rank risks that are loud-but-low-
probability vs quiet-but-high-impact, and drive to a prioritized
mitigation list we can execute before Friday.

**Launch-relevant facts (from project context):**
- Payments API v2 is deployed; contract at `api/v2.yaml`.
- Coupon endpoint `/v2/coupons/apply` was added to v2 this week
  after a cross-team scramble. Not yet battle-tested.
- Release is feature-flagged. Flag default OFF at Friday ship, ramp
  per-user over the weekend to 100% Monday.
- Legacy payments API goes read-only Saturday (hard deadline from
  the payments team).
- Compliance requires clean audit log for all transactions Monday
  onward.
- PM is out Tuesday and Wednesday, back Thursday.
- Team: engineer, ops, support. No dedicated legal, compliance,
  security, or marketing reviewer on this pre-mortem.

**Team:** engineer, ops, support. PM runs the pre-mortem.

**Output:** `OUTPUT.md` — top risks prioritized (impact × likelihood),
dropped risks with rationale, gaps surfaced, this-week mitigation
commitments with owners, and what we'll watch in the week after
launch.
