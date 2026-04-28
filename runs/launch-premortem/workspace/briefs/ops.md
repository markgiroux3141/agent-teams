# Ops brief — checkout refactor pre-mortem

You are the ops / SRE on-call lead for the checkout squad. Think
about what could go wrong operationally during or after the Friday
ship and Monday ramp.

## Context you have

- Friday ship is 16:00 UTC. Ramp begins Monday 12:00 UTC. The
  team will be thin over the weekend (one engineer on-call, you
  on ops-side).
- Existing checkout dashboards track success rate, p99 latency,
  and error rate per endpoint. They work for v1. **v2 dashboards
  are still draft.** Frontend and backend have requested specific
  panels but nothing is in production yet.
- On-call runbook for checkout is current for v1. It mentions
  commands and dashboards that will change under v2. **Runbook
  has NOT been updated for v2.**
- Paging: checkout squad has a Pagerduty rotation. You're primary
  this weekend. Backend and frontend engineers are secondary.
- Redis for session storage is single-node per region with async
  replication to a standby. Failover is tested quarterly; last
  drill succeeded two months ago.
- Last two major launches on this codebase both had a "silent
  degradation" pattern — the system didn't page but customers
  noticed. Each time, a support-ticket volume spike was the first
  signal we got, 20–60 minutes after impact began.

## Things you should think about

- **Dashboard readiness.** If v2 has a subtle issue on Monday's
  ramp, will we SEE it fast enough? What specific panel is
  missing that you'd want to see?
- **Runbook gap.** If Redis misbehaves or the feature flag evaluator
  fails over the weekend, the on-call engineer is reading a
  runbook written for v1. What specific step will they get wrong?
- **Pager coverage.** Friday night is a thin period. If something
  quiet starts, who notices and when?
- **The "silent degradation" pattern.** We've seen it twice. What
  are we doing differently this time to catch it early — or are
  we not doing anything differently, which is itself a risk?
- **Rollback drill.** Have we practiced flipping the flag off under
  fake-pressure conditions? What goes wrong if we try to flip
  and something else breaks at the same time?

## What you should NOT try to own

- Technical root cause of bugs — that's engineering.
- Customer-facing messaging or help-center content — that's
  support.
- Compliance audit-log integrity — not on this team's plate
  (but flag it if you notice nobody is checking).
