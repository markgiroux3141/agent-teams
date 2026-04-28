# Pre-mortem — Checkout refactor launch

## Imagined Failure State (the prompt)

> It is now Monday 2026-04-27, the day after the 100% ramp.
> The launch went badly. Something about the cutover has caused
> enough pain that we are discussing rollback.
>
> **WHY?** What happened? What did we fail to see coming?

## Context
- **Launch:** Friday 2026-04-24 (feature-flagged OFF), ramping to 100% Monday 2026-04-27
- **Scope:** Payments API v2 + new React checkout flow
- **Key constraints:**
  - Coupon endpoint `/v2/coupons/apply` added to v2 this week, not battle-tested
  - Legacy payments API goes read-only Saturday 2026-04-25 (hard deadline)
  - Compliance requires clean audit log for all transactions Monday onward
  - PM out Tuesday–Wednesday 2026-04-22–23, back Thursday
- **Roster:** engineer (technical), ops (operational), support (user-facing)
- **No dedicated reviewers:** legal, compliance, security, or marketing

## Contributor Format

Each role must write `risks/<role>.md` with this exact format:

```markdown
## Failure modes

- <risk name> (likelihood: high/med/low, impact: high/med/low)
  Mechanism: <what would actually go wrong, specifically>
  Early signal: <what you'd see first if it were starting>

[repeat 3–5 times]

## Mitigations I'd invest in this sprint

- <risk name>: <specific preventive or detection action>

[repeat for each risk]
```

## Rules

- Surface 3–5 failure modes from your angle
- For each: be specific about mechanism and early signal
- **CROSS-ROLE RULE:** If your risk implicates another role's domain (e.g., an engineering risk that would blow up support volume), send a `send_message` to that peer. The lead is CC'd automatically.
- Follow your system prompt exactly

## Timeline

- **Phase 1 (now):** Each role brainstorms and writes risks/<role>.md (in parallel)
- **Phase 2 (after Phase 1):** Lead clusters duplicates, finds gaps, rebalances scale, and dispatches follow-ups
- **Phase 3 (after Phase 2):** Finalize and deliver OUTPUT.md
