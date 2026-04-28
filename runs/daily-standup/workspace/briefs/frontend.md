# Frontend brief — 2026-04-22

## Yesterday
- Scaffolded the new `<CheckoutV2>` component tree and wired it to the
  feature flag (`checkout_v2_enabled`). Flag default off; turn on per
  user for QA.
- Hooked up the transaction submit flow against `/v2/transactions`.
  Smoke test in staging works for the happy path.
- Blocked on the coupon endpoint. What I'm building against is the
  mock from last sprint (`/v2/coupons/apply`, returns a discount
  object). I haven't seen it in the v2 contract and backend hasn't
  confirmed it's real.
- Asked design for the final empty-state mocks. Haven't heard back.

## Today
- Coupon flow, assuming the endpoint lands today.
- Error states: declined card, expired session, network timeout. I
  have placeholder copy; waiting on design's final pass before I
  replace it.
- Behind-the-flag merge so we can ramp on Monday without a big-bang
  cutover.

## Concerns
- If coupons aren't in v2, we can't ship with feature parity. That's
  a release blocker, not a nice-to-have.
- The release plan doc says "full cutover Friday" but eng lead told me
  in the weekly "flag it and ramp". I've been building for the flag
  path. Need someone to say which one is real.
- No mocks for the new confirmation screen post-refund. QA will ask.
