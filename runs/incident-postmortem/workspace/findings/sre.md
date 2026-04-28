# SRE findings — incident 2026-04-20

## Evidence

- HTTP 401 spike on `/session/validate` starting 14:02:14 UTC (baseline ~3 req/min → peak ~310 req/min at 14:18 UTC)
- All 401 responses carry identical error signature: `{"error":"session_expired","code":"SES_EXP"}`
- Session invalidation pattern shows same session_id cycling: valid → 401 → new session issued → valid → 401 again, within 2–3 minute windows
- Example: `sid=a7f2…` succeeded at 14:08:22, failed at 14:08:44 (22 seconds later); new `sid=b3e9…` succeeded at 14:09:01, failed at 14:11:53 (168 seconds later)
- Non-session endpoints and `/healthz` remained clean throughout; no gateway errors
- No process crashes, OOM kills, or database connectivity drops in incident window
- Recovery curve begins 14:36 UTC, returns to baseline 14:42 UTC (correlates with rollback triggered at 14:35)

## Timeline (my view)

- 14:00 UTC — baseline session validation rate ~3 req/min
- 14:01 UTC — deploy executed (deploy details unknown to SRE)
- 14:02:14 UTC — 401 spike begins on `/session/validate`
- 14:05 UTC — scheduled DB failover occurs (failover details unknown to SRE)
- 14:18 UTC — peak error rate reached (~310 req/min 401s)
- 14:35 UTC — rollback triggered
- 14:36 UTC — recovery begins (error rate starts declining)
- 14:42 UTC — error rate returns to baseline

## Initial hypothesis

The session system is prematurely invalidating valid sessions. The timing (14:02:14 start, only 71 seconds after deploy completion at 14:01) and the pattern (same user re-authenticating every 2–3 minutes instead of normal session lifetime) suggest either:

1. The 14:01 deploy modified session TTL values downward, or introduced a bug that marks sessions expired incorrectly
2. The 14:05 DB failover caused session records to be evicted from the session store ahead of their TTL, triggering the validation failures

The fact that 8% of checkouts succeeded suggests either a caching layer absorbed some validation calls, or certain traffic patterns (e.g., cached user flows) bypassed the session validation entirely.

Recovery correlated with rollback implies the root cause was in the deployed code, not in infrastructure state that persisted.

## Gaps / questions for others

- **releng**: What changed in the 14:01 deploy relative to the previous production version? Specifically: (a) any changes to session TTL configuration, (b) any changes to the session validation code path, (c) any dependency version bumps that could affect session lifecycle?
- **observability**: Can you confirm the exact moment the DB failover completed at 14:05? Did you observe any immediate spike in session cache evictions, memory pressure, or connection pool exhaustion on the session store during or immediately after the failover?
- **observability**: Did the cache hit rate on session lookups drop during the 14:02–14:35 window? If sessions were being evicted prematurely, cache-miss rate should spike.
- **support**: Can you confirm from customer tickets whether users reported being forced to re-login multiple times during 14:02–14:35, and roughly how many re-auth cycles each user experienced before giving up?
