# Release Strategy Clarification — 2026-04-22

## Conflict Summary

- **Backend brief** states: "Kick off the full-cutover checklist: DNS flip script, old-API read-only toggle, rollback plan."
- **Frontend and QA** are building for feature-flag rollout with Monday ramp-up.
- **Release doc** says "full cutover Friday" (cited but not in-hand).
- **Eng lead weekly** said "flag it and ramp" (cited but not in-hand).

## Official Position

Per **DONE_CRITERIA.md** (project context, Day 3 of 5):

**Feature-flagged rollout, ramp to 100% Monday if metrics hold.**

This is the authoritative source. Not a hard cutover Friday.

## Decision

Release strategy is **feature-flag rollout**:
- Flag default OFF Friday
- Enable per-user/gradual ramp Monday
- NO DNS flip or hard cutover Friday
- Keep old API live through Monday ramp period

## Implications for Backend

My brief is outdated/incorrect. Work to adjust:
- ✅ Do NOT kick off full-cutover checklist (DNS flip, read-only toggle)
- ✅ DO build flag infrastructure: feature flag storage, v2 routing logic, metrics hooks
- ✅ Idempotency-key header still needed (compliance audit log, Monday onward)
- ✅ Refunds/transactions endpoints ready as-is
- ✅ Plan rollback via flag toggle, not DNS revert

## For Frontend and QA

Frontend: Build checkout component with **feature flag integration**. No hard cutover assumption.

QA: Build test plan for **ramp validation** (flag on/off switching, metrics, gradual traffic). Not cutover validation.

## Next Steps

1. Backend: Adjust cutover checklist → flag infrastructure plan
2. Frontend: Confirm flag integration path with this clarity
3. QA: Adjust test scope from cutover to ramp validation
4. All: Confirm readiness by EOD for Friday ship

**This is the binding decision.** If the release doc contradicts DONE_CRITERIA, DONE_CRITERIA wins.
