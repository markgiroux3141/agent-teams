# Backend — Wednesday, 2026-04-22

## Yesterday
- Shipped payments API v2 to staging. Migration ran clean, deploy green.
- Wired `/v2/transactions` and `/v2/refunds` endpoints with integration tests passing.
- Pushed OpenAPI contract to `api/v2.yaml`.

## Today
- Add idempotency-key header to `/v2/transactions` (compliance audit log requirement).
- Kick off full-cutover checklist: DNS flip script, old-API read-only toggle, rollback plan.
- Review frontend PR when ready.

## Blockers
- None.

## Questions for the team
- Frontend: Does v2.yaml have everything you need for the new checkout flow?
- QA: Staging status on regression testing — any blockers?
