# Backend brief — 2026-04-22

## Yesterday
- Shipped payments API v2 to staging. Migration ran clean on Monday,
  deploy green.
- Wired the new `/v2/transactions` and `/v2/refunds` endpoints; both
  have integration tests passing.
- Pushed the OpenAPI contract to `api/v2.yaml`. Frontend should be
  unblocked now — everything they asked for in sprint planning is in
  there.
- Skim'd the design doc on the plane back from the offsite. PM told me
  in Slack last Thursday that the designs are locked; I'm treating the
  mocks in the Figma link as the source of truth.

## Today
- Add the idempotency-key header to `/v2/transactions`. Compliance
  needs it for the audit log.
- Kick off the full-cutover checklist: DNS flip script, old-API
  read-only toggle, rollback plan. Friday ships, so today is the last
  day to close out infra.
- Review frontend's PR when it's ready.

## Concerns
- Legacy API goes read-only Saturday per Payments team. If anything
  slips past Friday we have to extend that window, which is
  cross-org.
- Nothing on my radar from QA. I assume staging is green for them.
