# Design review — RateGuard (rate-limit service)

## Design under review

**Project:** RateGuard — new rate-limit service to protect the public API from abuse.

**Key claims from the design:**
- Uses IP-based client identification; rate limits tracked per IP (100 tokens, refill 10/sec default)
- Token bucket algorithm stored in Redis; Lua scripts for atomic read+decrement
- Deployed as sidecars alongside API pods (sidecar fronts each pod)
- Multi-region, active-active rollout (us-east-1 and eu-west-1 hit same service; Redis per-region with async replication)
- Latency target: < 100ms p99 added to protected requests (hard SLA); team claims < 10ms p99 total added latency
- Throughput: single Redis node ~80k ops/sec per region; API peak ~15k rps
- Fail-open on Redis unavailability (allow all traffic if Redis is down)

**Ship plan:** Staging rollout in 2 weeks; production end of Q2.

---

## Review roster

- **presenter** — senior backend engineer, design author. Role: defend the design and answer specific questions.
- **security** — security reviewer. Standing context: 3+ prior rate-limit designs reviewed; company has been burned by over-trusting IP-based identifiers (Q4 2024 coupon abuse via residential proxies, Q1 2025 NAT sharing issue, Q3 2024 carrier NAT issue).
- **perf** — performance reviewer. Standing context: 4+ Redis designs reviewed; pattern is under-modeling multi-region complexity (e.g., Q2 2025 session service cross-region Redis latency blowup, Q4 2024 active-active Redis single-node bottleneck).

---

## Required output format

### PRESENTER (initial summary)

Write to `summary/presenter.md`. Format:

```
## Design summary
- <key claims from the design, bullet list>

## Risks I acknowledge
- <risks the design doc already names>

## Invariants I rely on
- <assumptions I'm making that others should verify>
```

Do NOT preemptively rebut critiques — you will get a dedicated rebuttal round.

### CRITIC (security or perf)

Write to `critiques/security.md` or `critiques/perf.md` (per role). Format:

```
## Critiques (substantiated only)
- <critique title> — evidence: <specific mechanism or prior incident that shows this is a real risk>
- <critique title> — evidence: <...>

## Questions for the presenter
- <specific, answerable question>
- <...>
```

**Rule:** Only include critiques where you can point to a mechanism or prior incident. Drop concerns that are vague or naming-only. If a critique has cross-domain implications (e.g., security finding that affects perf, or perf risk that affects security), call it out via `send_message` to the other reviewer.

---

## Review process

1. **Phase 1 (parallel):** Presenter summarizes design. Security and perf critique independently.
2. **Phase 2 (triage):** Tech Lead reads all three, triages critiques (substantiated vs. dropped), identifies cross-domain issues, dispatches a rebuttal task to presenter.
3. **Phase 3 (verdict):** After rebuttal, Tech Lead issues verdict (APPROVE / REVISE / BLOCK) with concrete required changes.

---

## Output artifact

`OUTPUT.md` — final verdict, substantiated critiques with resolutions, required revisions with owners and due dates.
