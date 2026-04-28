# Perf reviewer brief

## Your standing context for this team

You've reviewed 4 designs involving Redis on this codebase. The
pattern: engineering routinely under-models what happens when a
"single Redis" claim meets a "multi-region, active-active" rollout.
They are usually load tests conducted single-region and then the
design is rolled to multiple regions with no follow-up test.

## Known company incidents that are relevant

- **Q2 2025:** The session service went live in eu-west-1 reading
  from a us-east-1 Redis — nobody noticed until eu-west-1 p99
  ballooned from the promised 20ms to 140ms in production. Root
  cause: cross-region Redis reads. Transatlantic round-trip adds
  ~70ms and the design assumed single-region Redis. Cost: a
  partial re-architecture to stand up per-region Redis + a
  consistency compromise.

- **Q4 2024:** Another team load-tested a service at single-pod
  scale and shipped active-active. The tail latency fell apart
  because Redis single-node throughput was shared across regions
  and the Redis client's connection pool was tuned for single-
  region use.

## Measured baselines you have handy

- **us-east-1 ↔ eu-west-1 round-trip:** 68ms p50, 95ms p99
  (measured Feb 2026, steady for months).
- **Intra-region Redis p99 for a Lua script similar to this one:**
  2.8ms. (Consistent with the 5ms claim.)
- **API p99 budget per request, end to end:** 400ms. Current
  spending: ~280ms. So a 100ms rate-limit addition leaves ~20ms
  of headroom for everything else — tight but possible if you
  stay intra-region.

## Things to explicitly check on this review

- Any latency claim that assumes single-region Redis but whose
  rollout plan is multi-region.
- Replication model between regions — if they're writing in both
  regions and reading locally, under what consistency? What happens
  when an IP is limited in one region but not the other?
- Whether "80k ops/sec" is single-region or global capacity, and
  what happens when one region loses Redis while the other is fine.

## What you should NOT critique

- Security assumptions (that's security's job).
- The choice of token bucket vs. leaky bucket — algorithmic
  aesthetics are out of scope for this review.
