# QA brief — 2026-04-22

## Yesterday
- Ported 14 of the 22 existing regression tests to the new endpoints.
  8 remaining are the coupon + refund cases; I can't finish those
  until the endpoints are settled.
- Noticed the staging DB came up empty-ish after Monday's migration.
  Half the fixture users are missing, the `promo_codes` table is
  empty. Tests that depend on a real user loading a saved card all
  fail. I don't know if this is on me, backend, or infra — the seed
  script lives in `infra/seed/` but nobody's name is on it.
- Drafted the test plan for the Friday launch. Kept it generic
  pending the cutover-vs-flag call.

## Today
- Unblock the staging seed. Somebody has to own this today or we
  can't run the full suite before Friday.
- Write the refund regression cases once the endpoint shape is
  confirmed.
- Exploratory testing on the checkout_v2 flag — need frontend to flip
  it on for my test user.

## Concerns
- Staging seed is a hard blocker for me. It's also a hard blocker for
  any end-to-end sign-off before ship.
- The release plan doc and eng lead are saying different things about
  cutover vs flag. My test plan is different for each; I need a
  decision by EOD.
- No confirmation screen mocks for the refund path. Can't validate
  copy without them.
