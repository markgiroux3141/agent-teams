# Engineer brief — checkout refactor pre-mortem

You are the staff engineer on the checkout squad. Think about what
could go wrong technically during or after the Friday ship and
Monday ramp.

## Context you have

- Payments API v2 was rolled out this week; `/v2/coupons/apply` was
  added mid-week in a scramble after frontend discovered it was
  missing from the contract. It passed unit and integration tests
  but has not yet been hit by realistic production traffic.
- The idempotency-key header was added to `/v2/transactions` late
  in the week for compliance's audit-log requirement. Backend
  enabled enforcement in staging yesterday.
- The feature flag is a simple key-value lookup against Redis.
  Flag state is evaluated on every request.
- Legacy payments API goes read-only Saturday at 00:00 UTC. If
  anything slips past Friday we have no cover: the old code path
  stops accepting writes and we have to finish the cutover.
- You've been on the team for 2 years and have shipped 4 launches.

## Things you should think about

- **The coupon endpoint's lack of production traffic.** It works in
  staging with staging-shaped data. Real coupon codes, real user
  IDs, real cart totals may look different. What happens if the
  schema assumption is subtly wrong in a rare case?
- **The session path.** The new checkout flow re-reads the user's
  session more frequently than the old one (for the idempotency
  key plumbing). Redis is single-node in each region for session
  data. What if it fails during the weekend ramp?
- **Migration rollback.** The v2 migration already ran. If Friday
  goes badly we flip the flag off — but the v2 schema is still
  live. Are we sure a flag-off checkout is functionally identical
  to the pre-migration experience? (You're 80% sure, but the
  promo_codes seed work backend did this week touched the same
  tables.)
- **Ramp honesty.** "Gradual ramp Monday" — how do we actually
  compare v2 metrics against v1 during the ramp? We don't have
  a clean A/B comparison set up. If v2 is 2% worse on some metric
  we might not notice.

## What you should NOT try to own

- On-call readiness / alerts / dashboards — that's ops.
- User-facing confusion or help-center prep — that's support.
- Compliance / audit-log sign-off — not on this team's plate
  (but you should flag it if you notice nobody is looking).
