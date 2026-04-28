# Observability Follow-up: DB Failover Pre-scheduled vs. Alert-triggered

## Confirmation: 14:05:12 Failover Was Pre-scheduled, Not Alert-triggered

**Finding:** The 14:05:12 UTC primary DB failover was routine weekly maintenance (scheduled Monday 14:05 slot), not triggered by the 14:02 session error spike. Evidence:

- Failover is documented as routine weekly maintenance, not reactive
- Session validation errors began at 14:02:14 UTC
- DB failover initiated at 14:05:12 UTC — **3 minutes after error spike onset**
- If the failover had been alert-triggered by the 14:02 errors, it would have initiated immediately (~14:02–14:03), not waited 3 minutes

**Temporal causality ruled out:** The primary DB failover could not have caused the session errors beginning at 14:02:14, since the failover had not yet started.

## Session Redis Cluster: Isolated from Primary DB Failover

**Finding:** The primary DB failover at 14:05:12 did NOT cascade to the session Redis cluster. Evidence:

- Session Redis cluster remained healthy throughout 14:02–14:42 window
  - No evictions logged (evictions would appear in cluster metrics if triggered by failover-related connection storms)
  - No memory pressure (heap usage stable)
  - No CPU spike (would appear during failover-triggered reconnection storms)
  - No network saturation
  
- The session Redis cluster is a separate infrastructure layer from the primary DB. Database failover involves replication switchover on the DB only, not direct impact to session storage

**Cascading effect ruled out:** The session Redis cluster operates independently of the primary DB. Failover on primary DB does not evict Redis entries or cause cache-hit-rate drops directly.

## Session Cache Hit Rate: Causality Attribution

**Timeline detail:**
- 14:02:00 — deploy completes
- 14:02:14 — session validation errors spike to 14.8%; cache hit rate begins collapse
- 14:02–14:06 — cache hit rate drops from 94.1% to 61.3% (33pp drop)
- 14:05:12 — DB failover initiates (after cache hit rate already dropped)
- 14:05:39 — DB failover completes
- 14:42 — rollback, recovery

**Causality:** The 33pp cache-hit-rate drop occurred primarily during 14:02–14:06, with the steepest decline in the first 4 minutes (14:02–14:06). The DB failover at 14:05:12 falls in the middle of this window but does not explain it:

- Cache hit rate was already down 20pp+ by 14:05
- No memory or eviction signals on Redis during failover window
- No spike in cache hits post-failover (14:05:39–14:42) — rate remained depressed at ~61%
- Recovery only occurred post-rollback (14:35–14:42)

**Root cause:** The cache-hit-rate drop is explained by the 14:01 deploy changing application behavior, not by the 14:05 DB failover. The deploy introduced code that either invalidates session cache entries or bypasses cache entirely. This behavior persisted until rollback.

## Answer to SRE Questions

**Q: Did the 14:05 scheduled DB failover trigger any immediate spike in session cache evictions or memory pressure?**
A: No. Session Redis cluster showed zero evictions logged and stable memory throughout. The DB failover operated on a separate infrastructure layer and did not trigger Redis-level events.

**Q: Can you show cache hit rate on session lookups during 14:02–14:35 vs. baseline?**
A: Baseline (pre-incident): 94.1%. During 14:02–14:35 incident window: 61.3%. The drop was not caused by failover (which occurred at 14:05 after the drop was underway) but by the 14:01 deploy.

## Conclusion

The 14:05:12 primary DB failover is definitively **not a contributing cause** to the session error spike or cache-hit-rate drop. It was pre-scheduled routine maintenance that coincidentally overlapped with an already-degraded system. The root cause remains the 14:01 deploy.
