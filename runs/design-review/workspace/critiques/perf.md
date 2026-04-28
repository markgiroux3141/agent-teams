# Performance Review — RateGuard

## Critiques (substantiated only)

- **Ambiguous multi-region architecture may violate latency SLA** — Evidence: The design states "us-east-1 and eu-west-1 hit same service" while claiming "Redis per-region with async replication." This is ambiguous: if "hit same service" means centralized RateGuard (all traffic routes through one region), sidecars in eu-west-1 would read from us-east-1 Redis. Cross-region round-trip latency is 95ms p99 (measured Feb 2026). This single hop consumes 95% of the stated 100ms p99 SLA target, leaving zero headroom and directly contradicting the claim of < 10ms p99 added latency. The Q2 2025 session service incident is the exact precedent: eu-west-1 reading from us-east-1 Redis caused p99 to balloon from 20ms to 140ms in production. If this interpretation is correct, the design fails the SLA immediately on cross-region reads.

## Questions for the presenter

- Is RateGuard deployed as a centralized service (all traffic routes through one region) or distributed per-region (sidecars in each region read local Redis)?

- If distributed per-region, explicitly confirm there are no cross-region reads on the critical request path (i.e., eu-west-1 sidecars read from eu-west-1 Redis locally, not from us-east-1).

- What is the measured p99 latency under production deployment (multi-pod, multiple distinct client IPs)? Current test was single-pod sidecar with single-IP traffic at 10k rps. The Q4 2024 incident shows single-pod testing can mask multi-pod production failures. Although the design has 5.33x throughput headroom (15k rps vs 80k ops/sec), empirical p99 measurement at production scale would validate the < 10ms claim.

- How is the Redis client connection pool configured for multi-pod deployment? The Q4 2024 incident cited "connection pool was tuned for single-region use" as a cause of tail latency collapse. Confirm pool sizing accounts for expected per-region sidecar count (estimated 10-20 pods per region).
