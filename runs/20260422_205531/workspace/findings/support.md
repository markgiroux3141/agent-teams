# Support findings — incident 2026-04-20

## Evidence

- 38 of 47 tickets (81%) report users successfully logging in, then being forcibly logged out during checkout, with multiple re-login cycles required to complete purchase
- Pattern timing cue: users consistently report sessions expiring ~2–5 minutes after re-login, then requiring another login
- Representative quote from ticket #18422: "I logged in fine, added items to my cart, clicked checkout, and it told me my session expired. I logged back in and tried again. It worked for a couple of minutes and then kicked me out again."
- Ticket #18431: "Got logged out mid-checkout THREE times before it let me pay."
- Ticket #18444: "I was logged in, went to add a coupon, got an error saying I was signed out. Signed in, tried again, was fine for about 5 minutes, then got signed out again."
- Ticket #18461: "Kept getting 'session expired' even though I hadn't even closed the tab. I was still in the middle of typing my card number."
- Ticket #18409: "This has never happened to me before. I don't think it's my wifi. I was on my phone too and had the same thing happen." (indicates platform-independent behavior)
- Secondary noise: 6 tickets about general site slowness (no session component), 3 about coupon codes (ambiguous relevance)
- All complaints are about session behavior, not login failure — users successfully authenticated but established sessions were killed prematurely

## Timeline (my view)

- 14:00–14:02 UTC — no reported session issues in queue
- 14:02 UTC onward — session expiration complaints begin arriving
- 14:02–14:35 UTC — 38 tickets accumulate with consistent re-login pattern
- 14:35 UTC — rollback triggered
- 14:42 UTC onward — new tickets stop reporting session cycling (last problematic ticket logged ~14:38 UTC)

## Initial hypothesis

The session TTL or session validation logic was changed in the 14:01 deploy, causing all established user sessions to be invalidated or expired every 2–5 minutes instead of persisting for the normal session lifetime. This forced users to re-authenticate mid-transaction, resulting in checkout abandonment and frustration.

This aligns precisely with SRE's observation of `/session/validate` returning 401s with `session_expired` error codes in a 2–3 minute cycling pattern. The customer-visible symptom is "get logged out, re-login, works briefly, get logged out again" — exactly what the session cycling data shows.

The fact that some checkouts succeeded (8% success rate vs 92% failure) suggests either:
1. A small fraction of users' sessions avoided the invalidation bug (caching or specific request patterns)
2. Some users completed checkout before hitting the second re-login cycle

## Gaps / questions for others

- **releng**: SRE is already asking this, but from support's angle — did the 14:01 deploy modify session TTL configuration, session validation code, or session storage interaction? The precision of the 2–3 minute window suggests a hardcoded value, not a random failure.
- **observability**: Were there any metrics changes (session cache hit rate, session store latency) between 14:01 and 14:02 that would correlate with the sudden session invalidation spike?

