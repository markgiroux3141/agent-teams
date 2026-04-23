# SRE brief — incident 2026-04-20

## What I have

Application logs from the checkout service, session service, and API
gateway, filtered to the incident window 14:00–14:45 UTC.

## Observations

**Error pattern:** Sharp spike in HTTP 401 responses on
`/session/validate` starting 14:02:14 UTC. Baseline was ~3 req/min;
peak was ~310 req/min at 14:18. Recovery curve begins 14:36, back to
baseline 14:42.

**401 response bodies (sampled, all identical):**
```
{"error":"session_expired","code":"SES_EXP","trace_id":"..."}
```

**Curious pattern in the logs:** The same session_id appears in
`/session/validate` several times in a row — succeeding, then
failing, then (after re-auth) succeeding again, then failing again
within a few minutes.

Example trace (redacted):
```
14:08:22  sid=a7f2… validate OK   user_id=u_184
14:08:44  sid=a7f2… validate 401  SES_EXP
14:09:01  sid=b3e9… (new sid) validate OK  user_id=u_184
14:11:53  sid=b3e9… validate 401  SES_EXP
```

Same user, re-authenticated twice in ~3 minutes, each new session
dying within minutes.

**What this is NOT:**
- Not a gateway issue. `/healthz` and non-session endpoints were
  clean throughout.
- Not a database connectivity event. Query logs to the primary
  session store are continuous through the window.
- No process crashes or OOM kills in the incident window.

## My initial read

The session system produced the 401s — that much is clear. The
pattern (valid → expired → valid → expired) looks more like
*unexpected session invalidation* than like normal expiry or an auth
outage. If sessions were being invalidated prematurely, I'd expect
this exact pattern.

## What I don't know

- Why sessions are being invalidated early. The code path that
  emits SES_EXP is the TTL check; either TTLs are wrong or
  session records are being evicted before their TTL.
- Whether this is the whole story. 92% of checkouts succeeded —
  some subset of users never hit this.
- Whether a deploy changed anything in the session path.
