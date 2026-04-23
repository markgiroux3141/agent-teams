# Frontend — Wednesday, 2026-04-22

## Yesterday
- Scaffolded CheckoutV2 component tree and wired to feature flag (checkout_v2_enabled), default off.
- Hooked up transaction submit flow against /v2/transactions; smoke test in staging passes on happy path.

## Today
- Implement coupon flow (pending endpoint confirmation from backend).
- Build error states: declined card, expired session, network timeout (pending design's final copy).
- Merge behind feature flag for Monday ramp-up.

## Blockers
- Coupon endpoint (/v2/coupons/apply) not confirmed in v2 contract — building against mock from last sprint. Feature parity blocker. (owner: backend)
- Error state copy from design not finalized.
- No mocks for new post-refund confirmation screen. (needs owner)

## Questions for the team
- Release plan doc says "full cutover Friday" but eng lead said "flag it and ramp" in weekly. Which is the actual plan?
