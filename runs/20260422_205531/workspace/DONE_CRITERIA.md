# Incident Postmortem Scope — Checkout degradation, 2026-04-20

## Incident Summary
Checkout success rate dropped from 99.8% to 92% between 14:02 and 14:42 UTC on Monday 2026-04-20. ~40 minutes. Recovery correlated with the release engineer triggering a rollback at 14:35. Severity: SEV-2. Revenue impact estimated ~$180k in lost/abandoned transactions.

**Core facts:**
- Something changed around 14:00–14:02 (deploy at 14:01 UTC)
- Rolling back at 14:35 recovered the system by 14:42
- The outage was NOT total — success rate dropped to 92%, not 0%
- Users who succeeded did so on their first try; users who failed did so with varying patterns

**Open questions entering postmortem:**
1. Is it auth/session system malfunction?
2. Did the 14:05 scheduled DB failover cause side effects?
3. Was the 14:01 deploy truly innocuous as claimed?
4. Is there more than one cause compounding?
5. Will this recur if we redeploy the rolled-back version?

## Investigators & Roles

- **sre**: Owns application logs. Focus on checkout service, session service, API gateway logs for 14:00–14:45 UTC.
- **observability**: Owns metrics and infrastructure events. Focus on time-series data, dashboards, cache behavior, failover events.
- **releng**: Owns deploy pipelines and release manifest. Focus on the 14:01 deploy contents, dependency changes, the rollback.
- **support**: Owns customer tickets and user-reported behavior. Focus on ticket patterns, customer descriptions of symptom behavior.

## Required Investigation Output Format

Each investigator must write `findings/<role>.md` with this exact structure:

```
## Evidence
- <specific observation from my data source>
- <another specific observation>
- ...

## Timeline (my view)
- HH:MM UTC — <event I observe>
- HH:MM UTC — <event I observe>
- ...

## Initial hypothesis
- <what I think happened based on my evidence>
- <why this fits the data I see>

## Gaps / questions for others
- <teammate name>: <specific question directed at them>
- <teammate name>: <specific question directed at them>
```

**Critical rule:** If your evidence implicates another domain, **send_message that teammate BEFORE marking your task complete**. Example: if you see a deploy-correlated change, message releng with your specific observation. The lead is CC'd automatically on all peer-to-peer messages.

## Triangulation Goal

The answer is NEVER in one domain's findings alone. Root cause emerges from JOINS between evidence streams:
- Does observability's cache-hit-rate drop match SRE's session invalidation spike?
- Does releng's package diff explain support's "re-login every few minutes" pattern?
- Can we date the start of SRE's 401 spike to the exact moment of the deploy completion?

## Postmortem Deliverable

Final `OUTPUT.md` must contain:
- **Timeline (consolidated):** HH:MM UTC events from all four domains
- **Root cause hypothesis:** One paragraph. Which agents' evidence supports it. What specifically happened, in causal order.
- **Counter-evidence considered:** What evidence would have pointed elsewhere and why it was ruled out, or remaining uncertainty.
- **Contributing factors:** Process, tooling, or organizational factors that let this happen.
- **Remediation:** Named owners + actions + deadlines.
- **Unknowns:** What we still can't explain, or "none".
