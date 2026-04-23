# QA — Wednesday, 2026-04-22

## Yesterday
- Ported 14 of 22 existing regression tests to new endpoints.
- Identified staging seed issue: fixture users and promo_codes table empty after migration. Blocks full regression suite.
- Drafted test plan pending cutover vs flag decision.

## Today
- Unblock staging seed ownership and fix.
- Write refund regression cases once endpoint shape confirmed.
- Run exploratory testing on checkout_v2 flag (waiting on frontend to flip it).

## Blockers
- Staging seed is broken and owns nobody. Needs backend or infra to claim.
- Release strategy conflict: release doc and eng lead saying different things (cutover vs flag). Blocks final test plan.

## Questions for the team
- Backend: Is staging seed your domain or infra's? Refund endpoint ready?
- Frontend: Can you flip checkout_v2 flag for test user? Which release strategy are we shipping?
