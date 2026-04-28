# RateGuard — Design Doc (DRAFT v0.3)

Author: senior backend eng
Status: Ready for review

## Problem

Our public API is hit by abuse traffic — scraping, credential
stuffing, coupon-code brute-forcing. We need a uniform way to apply
rate limits across all public endpoints without each service
rolling its own.

## Goals

- **Protect the API** from abuse traffic at the edge.
- **Low operational overhead** — no per-service tuning.
- **< 100ms p99 latency** added to protected requests (hard target).
- **Configuration via a single YAML** checked into the service repo.

## Non-goals

- Authentication — RateGuard trusts the identity already established
  at the edge gateway.
- Bot detection beyond rate. Not a WAF.
- Fine-grained per-tenant limits. V1 is global and per-identifier.

## Approach

### Identifier

Incoming requests are identified by **client IP address**. Rate
limits are tracked per IP. This is simple, doesn't require
application-layer changes, and handles unauthenticated traffic.

### Algorithm

**Token bucket** — each IP has a bucket of N tokens refilled at rate
R. Each request consumes 1 token. When the bucket is empty, the
request is rejected with HTTP 429.

Default: 100 tokens, refill 10/sec. Overridable per-endpoint in YAML.

### Storage

**Redis** — bucket state (token count, last-refill timestamp) per
IP, keyed as `ratelimit:{ip}:{endpoint}`. TTL 1 hour of inactivity.

We use a Lua script to read+decrement atomically.

### Deployment

RateGuard is a sidecar deployed alongside each API pod. The sidecar
fronts the pod — all inbound traffic goes through it first.

### Rollout plan

**Multi-region, active-active.** We ship to us-east-1 and eu-west-1
simultaneously. Both regions hit the same RateGuard service. Redis
is deployed per-region; writes are propagated via async replication.

### Claims

- **Latency:** Lua scripts on Redis complete in < 5ms p99 based on
  the team's internal benchmarks (single-region Redis, us-east-1).
  Total added latency to the request path: < 10ms p99. Headroom to
  the 100ms SLA is generous.
- **Throughput:** Redis single-node handles ~80k ops/sec per region
  which comfortably exceeds our API's current 15k rps peak.
- **Simple:** one sidecar, one Redis, one YAML. Nothing to tune
  per-service.

## Risks (acknowledged by the author)

- **Redis unavailability** — if Redis is down, fail-open (allow all
  traffic). This trades safety for uptime during infra outages.
- **Configuration drift** — YAML in the repo may lag actual traffic
  patterns. We'll review quarterly.

## Testing

- Unit tests of the Lua script.
- Integration test: hammer a canary endpoint from a fixed IP, verify
  429s at the expected rate.
- Load test: single-region only, single-pod sidecar, single-IP
  traffic — 10k rps sustained for 5 minutes. Latency p99 remained
  under 8ms.

## Ship date

Targeting production end of Q2. Staging rollout in 2 weeks.
