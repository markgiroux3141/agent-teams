# Observability brief — incident 2026-04-20

## What I have

Time-series metrics for the checkout service, session service, and
shared infrastructure (Redis cluster, primary DB, load balancers),
plus the infra event log.

## Key metric shifts

- **Checkout success rate:** 99.8% → 92.1% at 14:02; recovery at
  14:42. Not a cliff — a stepped degradation over ~4 minutes before
  stabilizing near 92%.
- **`/session/validate` error rate:** 0.2% → 14.8% at 14:02; peak
  ~18% around 14:20; recovery at 14:42.
- **Session Redis cluster — cache hit rate:** 94.1% → 61.3% during
  the window. Back to 93.7% by 14:45. **This is the most unusual
  thing in my data.** Normally it barely moves during a deploy or
  failover.
- **Session Redis cluster — memory pressure:** stable throughout.
  No evictions logged. No CPU spike. No network saturation.
- **Primary DB:** automated failover at 14:05:12 UTC, completed
  14:05:39. This is a routine weekly failover (Monday 14:05 is the
  scheduled slot). Applications tolerate it without data loss.
- **App-server CPU / memory:** flat.
- **Latency:** slightly elevated on `/session/validate` (p99 went
  from ~40ms to ~120ms) but within tolerances.

## Infra events in the window

- 14:01:12 — deploy webhook fired (release-bot, target: checkout
  service fleet, all regions)
- 14:05:12 — primary DB failover (scheduled, weekly)
- 14:35:07 — deploy webhook fired (rollback to prior version)

## My initial read

The Redis cache-hit-rate drop is the strangest signal. The cluster
itself was healthy (no evictions, no memory issues) — so **the cache
wasn't failing, it was being bypassed or invalidated**. The pattern
does not match a Redis outage; it matches code asking for a key that
the cache believes no longer exists.

The DB failover at 14:05 is routine and started AFTER the symptoms
began (14:02). Unlikely to be causal.

The deploy at 14:01 timing-aligns with incident onset.

## What I don't know

- What code path changed that would invalidate cached session
  entries or ask for keys the cache doesn't hold.
- Whether the cache-hit drop is a consequence of the 401s (users
  re-authenticating churns the cache) or the cause.
- What actually shipped at 14:01.
