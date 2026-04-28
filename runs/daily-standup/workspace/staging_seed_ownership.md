# Staging Seed Ownership — 2026-04-22

## Decision

**Backend claims ownership of staging DB seed fix.**

## Reasoning

1. **Root cause:** Backend's v2 migration Monday 04-20 broke the seed script.
2. **No infra contact:** Project team is backend + frontend + qa only. No infra team assigned.
3. **Critical blocker:** QA cannot run regression suite without fixture data. Friday ship depends on staging health.
4. **Ownership:** Backend migration → backend fix.

## Commitment to QA

- Fix staging seed script in `infra/seed/` to restore fixture users and promo_codes table
- Re-run migration on staging DB
- Verify fixture data population
- **ETA: by EOD today (6 hours)**

## What Broke

Post-v2 migration (Monday):
- Fixture users missing (should be ~20, down to ~10)
- promo_codes table empty (needed for coupon flow validation)
- Tests depending on saved card fixtures fail

## Fix Scope

1. Update seed script for v2 schema
2. Verify fixture user IDs and card tokens still valid
3. Verify promo_codes data is seeded correctly
4. Refresh staging DB
5. Confirm QA can run full regression suite

## Unblocks

- QA's regression testing for Friday sign-off
- Coupon flow end-to-end validation
- Refund path validation
