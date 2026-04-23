# Rebuttal to substantiated critiques

## Critique 1: IP-based rate limiting does not protect against distributed proxy abuse
- **Your response:** Accept
- **Rationale:** The critique is correct. The Q4 2024 coupon-brute-force incident demonstrates that per-IP limits alone fail when an attacker rotates through proxy pools. The design's assumption that "one IP = one attacker" is false. I will revise the design to add a secondary behavioral rate-limit layer that detects proxy rotation via fingerprinting (user agent changes, request header variation, geolocation inconsistency, request timing patterns). This layer will apply an aggregate rate limit across requests that appear to originate from the same attacker despite IP rotation. Design doc update and implementation plan due by **May 20, 2026**.

---

## Critique 2: Legitimate aggregated traffic (corporate NATs, mobile carriers) is penalized equally with abusive traffic
- **Your response:** Accept
- **Rationale:** The critique is correct. The Q1 2025 B2B NAT incident and Q3 2024 mobile carrier incident show that per-IP-only rate limiting punishes legitimate users. I will revise the design to add per-API-key and per-user rate limits for authenticated requests, tracked as secondary limits alongside IP limits. For authenticated traffic, the more restrictive limit applies. For unauthenticated traffic, I will defer session-based rate limiting to a follow-up design (requires session identification at the API gateway, not currently available). Authenticated user rate limiting will be implemented by **June 1, 2026**.

---

## Critique 3: Fail-open on Redis unavailability defeats the rate-limiting goal during the moment it is most needed
- **Your response:** Defer
- **Rationale:** The critique correctly identifies a real trade-off that the design acknowledges but does not justify. I need to measure the actual operational impact of fail-closed (blocking traffic during Redis outage) on P99 latency, customer error rates, and revenue impact, then compare against the security cost of fail-open. I will measure both fail-open and fail-closed behavior in a staging environment, and commit to a decision (fail-open, fail-closed, or hybrid such as fail-closed-then-fallback) by **May 10, 2026**, backed by concrete metrics.

---

## Critique 4: Async replication across regions allows attackers to double-spend their rate-limit budget
- **Your response:** Accept
- **Rationale:** The critique is correct. The design does not specify replication latency targets, creating an undefended race window. I will revise the design to: (1) add an explicit SLA: async replication must complete within 100ms p99 across all regional pairs, with alerts on violations; (2) implement additional controls such as per-IP request debouncing (e.g., enforcing a minimum time between requests from the same IP to different regions) to narrow the exploitable window; (3) monitor replication lag in production and implement backpressure if it exceeds the SLA. Measurement plan and implementation due by **May 20, 2026**.

---

## Critique 5: No per-user or per-account rate limiting for authenticated requests, only IP-based limits
- **Your response:** Accept
- **Rationale:** The critique is correct. The design has no secondary per-user rate limit for authenticated requests, leaving compromised credentials and insider tokens exposed to abuse at the full per-IP rate. I will add per-API-key and per-user rate limits for authenticated requests (default: 1000 tokens, 50/sec, overridable per-endpoint in YAML), tracked alongside IP limits. For each request, the more restrictive of the IP limit and the per-user limit applies. This adds insider and credential-theft protection without changing the per-IP DDoS defense. Implementation due by **June 1, 2026**.

---

## Critique 6: Ambiguous multi-region architecture may violate latency SLA
- **Your response:** Accept
- **Rationale:** The critique is correct. The design doc states both "Both regions hit the same RateGuard service" and "Redis is deployed per-region," which is contradictory and creates ambiguity about whether sidecars in eu-west-1 read from us-east-1 Redis (violating the 100ms SLA). I will clarify the intended architecture in the design: each region (us-east-1, eu-west-1) has its own fleet of RateGuard sidecars and its own Redis instance. All rate-limit read+decrement operations are local (zero cross-region lookups). Async replication propagates state changes between regions for eventual consistency, introducing the race condition addressed in Critique 4. Revised design doc due by **May 3, 2026**.
