# Refund Endpoint Confirmation — 2026-04-22

## Status: LOCKED ✓

`/v2/refunds` endpoint is final and ready for QA regression testing.

## Details

- **Endpoint:** `/v2/refunds`
- **Status:** Wired and deployed to staging
- **Test coverage:** Integration tests passing
- **Ready for:** QA regression test case writing

## What This Unblocks

QA can now write the 8 remaining refund regression test cases (currently blocked, waiting for endpoint confirmation).

## Regression Test Cases for QA

- Refund success happy path
- Refund with partial amount
- Refund on already-refunded transaction
- Refund on expired transaction
- Refund with invalid transaction ID
- Refund network timeout / retry
- Refund unauthorized (wrong merchant key)
- Refund idempotency (same request twice)

All test writing can proceed now. Endpoint will not change.
