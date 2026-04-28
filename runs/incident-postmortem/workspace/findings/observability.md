# Observability Findings — Checkout Degradation 2026-04-20

## Evidence

- Checkout success rate: 99.8% → 92.1% at 14:02 UTC (stepped degradation over ~4 minutes, not a cliff)
- `/session/validate` error rate: 0.2% → 14.8% at 14:02 UTC; peak ~18% at 14:20 UTC; recovery to 0.2% at 14:42 UTC
- Session Redis cache-hit-rate: 94.1% → 61.3% during incident window; recovery to 93.7% by 14:45 UTC. **33 percentage point drop is anomalous.**
- Session Redis cluster health: stable throughout. No evictions logged, no CPU spike, no memory pressure, no network saturation. Cluster infrastructure was operational.
- `/session/validate` latency: p99 elevated from ~40ms to ~120ms, within tolerances
- App-server CPU and memory: flat, no anomalies
- Primary DB failover: 14:05:12 UTC initiated, 14:05:39 UTC completed. Routine weekly failover (scheduled Monday 14:05 slot). Applications tolerate without data loss.
- Deploy webhook: 14:01:12 UTC (checkout service fleet, all regions)
- Rollback webhook: 14:35:07 UTC

## Timeline (my view)

- 14:01:12 UTC — deploy webhook fired for checkout service fleet, all regions
- 14:02 UTC — checkout success rate drops to 92.1%, `/session/validate` error rate spikes to 14.8%
- 14:02–14:06 UTC — Session Redis cache-hit-rate collapses from 94.1% to 61.3%
- 14:05:12 UTC — primary DB failover initiated (routine, scheduled); completed 14:05:39 UTC
- 14:20 UTC — `/session/validate` error rate peaks at ~18%
- 14:35:07 UTC — rollback webhook fired
- 14:42 UTC — checkout success rate recovers to 99.8%, `/session/validate` errors drop to 0.2%, Session Redis cache-hit-rate recovers to 93.7%

## Initial hypothesis

The 14:01 deploy introduced a code change affecting session validation behavior. The symptom pattern — healthy Redis infrastructure but 33pp cache-hit-rate drop coinciding with error rate spike — indicates the application code path changed to either invalidate cached session entries at higher frequency, or bypass the Redis cache entirely for validation. This is not a Redis outage scenario; the cluster metrics show normal operation. The mechanism is application-level: changed code that alters how session cache is queried or invalidated. Recovery timing (14:42, minutes after rollback at 14:35) confirms the deploy was causal. The DB failover at 14:05 started after symptom onset (14:02) and is routine weekly maintenance, so timing correlation is coincidental.

## Gaps / questions for others

- releng: What specifically changed in the 14:01 checkout service deploy? Any modifications to session validation codepath, session cache key generation, or session invalidation logic?
- sre: Are the `/session/validate` errors 401 (auth failure) or another status code? And do your logs show cache misses followed by validation failures, or validation failures without a cache lookup attempt?
- sre: Can you cross-reference the Redis cache-hit-rate drop (14:02–14:06) with user authentication events or session object creations? A surge in session invalidation or re-authentication would churn the cache and partially explain the hit-rate drop.
- support: Are there customer reports of needing to re-login repeatedly or unexpectedly during the 14:02–14:42 UTC window?
