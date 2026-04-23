## Design summary

- **Identifier:** "Incoming requests are identified by client IP address. Rate limits are tracked per IP."
- **Algorithm:** Token bucket — "each IP has a bucket of N tokens refilled at rate R. Each request consumes 1 token. When the bucket is empty, the request is rejected with HTTP 429." Default: 100 tokens, refill 10/sec.
- **Storage:** Redis, keyed as `ratelimit:{ip}:{endpoint}` with 1-hour TTL. "We use a Lua script to read+decrement atomically."
- **Deployment:** "RateGuard is a sidecar deployed alongside each API pod. The sidecar fronts the pod — all inbound traffic goes through it first."
- **Multi-region topology:** "Both regions hit the same RateGuard service. Redis is deployed per-region; writes are propagated via async replication."
- **Latency:** "Lua scripts on Redis complete in < 5ms p99 based on the team's internal benchmarks (single-region Redis, us-east-1). Total added latency to the request path: < 10ms p99." Hard target: < 100ms p99 added.
- **Throughput:** "Redis single-node handles ~80k ops/sec per region which comfortably exceeds our API's current 15k rps peak."
- **Fail-open:** "if Redis is down, fail-open (allow all traffic)."

## Risks I acknowledge

- **Redis unavailability:** Design trades safety for uptime — "fail-open (allow all traffic). This trades safety for uptime during infra outages."
- **Configuration drift:** "YAML in the repo may lag actual traffic patterns. We'll review quarterly."

## Invariants I rely on

- IP address is a reliable and sufficient client identifier for rate limiting, including for unauthenticated traffic.
- Lua script latency benchmarks (< 5ms p99, measured in single-region us-east-1) translate to production conditions.
- Single Redis node per region can sustain 80k ops/sec under the actual traffic pattern (composition, keys, memory, replication overhead).
- Async replication of rate-limit state between regions is acceptable; eventual consistency of bucket counts across regions does not violate the abuse-protection goal.
- Sidecar fronting architecture introduces no additional latency beyond Redis + Lua overhead (network path, marshaling, pod-to-pod communication).
- One-hour TTL on inactive buckets is appropriate for the traffic patterns and does not result in unexpected bucket resets during legitimate user sessions.
- YAML configuration stored in the service repo is sufficient to tune per-endpoint limits; no runtime configuration system is required.
