# Design review — RateGuard (rate-limit service)

## Verdict
**REVISE.** The design identifies six substantiated vulnerabilities and gaps in the abuse-protection model and multi-region consistency. The presenter has committed to addressing all of them with concrete revisions and due dates. The design cannot proceed to staging until critical revisions (multi-region architecture clarification, async replication SLA, per-user rate limiting) are completed and validated.

---

## Substantiated critiques and resolutions

### Security: IP-based rate limiting does not protect against distributed proxy abuse
- **Evidence:** Q4 2024 coupon-brute-force attack used residential proxy rotation (~$0.50–1/GB cost). Per-IP limits failed because attacker had thousands of IPs.
- **Presenter's response:** Accept
- **Resolution:** Add behavioral fingerprinting layer to detect proxy rotation via user-agent changes, request header variation, geolocation inconsistency, and request timing patterns. Apply aggregate rate limit across requests from same attacker despite IP rotation. **Due May 20, 2026.**

### Security: Legitimate aggregated traffic (corporate NATs, mobile carriers) is penalized
- **Evidence:** Q1 2025 B2B customer (2000 employees behind single NAT) rate-limited on normal traffic; Q3 2024 mobile carrier NAT penalized legitimate users.
- **Presenter's response:** Accept
- **Resolution:** Add per-API-key and per-user rate limits for authenticated requests (secondary to IP limits). For authenticated traffic, the more restrictive limit applies. For unauthenticated traffic, defer session-based rate limiting to follow-up design (requires session identification at API gateway, not currently available). **Due June 1, 2026.**

### Security: Fail-open on Redis unavailability defeats rate-limiting goal
- **Evidence:** Design fails open (allows all traffic) when Redis is down, disabling primary defense during outages. Attackers can probe for unavailability or deliberately attack Redis infrastructure to trigger fail-open.
- **Presenter's response:** Defer
- **Resolution:** Measure fail-open vs fail-closed operational impact in staging: latency p99, customer error rates, revenue impact. Compare against security cost of each policy. Decide on final strategy (fail-open, fail-closed, or hybrid fail-closed-then-fallback) backed by concrete metrics. **Decision due May 10, 2026.**

### Security: Async replication allows attackers to double-spend rate-limit budget
- **Evidence:** Race condition: attacker exhausts budget in eu-west-1, then makes additional requests in us-east-1 before replication propagates. Regional caches momentarily inconsistent; attacker can exploit by targeting both regions in rapid succession.
- **Presenter's response:** Accept
- **Resolution:** (1) Add explicit SLA: async replication must complete within 100ms p99 across all regional pairs, with alerts on violations; (2) implement per-IP request debouncing (enforce minimum time between requests from same IP to different regions) to narrow exploitable window; (3) monitor replication lag in production with backpressure if SLA is exceeded. **Due May 20, 2026.**

### Security: No per-user/per-account rate limiting for authenticated requests
- **Evidence:** Design has only IP-based limits for authenticated users. Compromised credentials or insider tokens can abuse at full per-IP rate with no secondary defense.
- **Presenter's response:** Accept
- **Resolution:** Add per-API-key and per-user rate limits for authenticated requests (default: 1000 tokens, 50/sec, overridable per-endpoint in YAML). For each request, apply the more restrictive of IP limit and per-user limit. Provides insider and credential-theft protection without changing DDoS defense. **Due June 1, 2026.**

### Performance: Multi-region architecture ambiguity may violate latency SLA
- **Evidence:** Design states "regions hit same service" and "Redis per-region" (contradictory). If eu-west-1 reads from us-east-1 Redis, 95ms p99 cross-region latency violates 100ms SLA and contradicts <10ms claim. Q2 2025 session service incident: exact mistake caused p99 to balloon from 20ms to 140ms in production.
- **Presenter's response:** Accept
- **Resolution:** Clarify architecture: each region (us-east-1, eu-west-1) has its own RateGuard sidecar fleet and Redis instance. All rate-limit operations are local (zero cross-region reads on critical path). Async replication propagates state changes between regions for eventual consistency (introducing the race condition addressed separately). **Due May 3, 2026.**

---

## Dropped (superficial) critiques
- None. All critiques filed were substantiated by mechanism or prior incident.

---

## Required revisions (concrete, testable, with owners and deadlines)

| Revision | Owner | Due Date | Specificity |
|----------|-------|----------|-------------|
| Clarify multi-region architecture (local-only reads, no cross-region latency on critical path) | Presenter | May 3, 2026 | Updated design doc must explicitly state: each region has own sidecars + Redis, all reads local, async replication propagates to other regions |
| Measure fail-open vs fail-closed impact and decide strategy | Presenter | May 10, 2026 | Staging experiment: measure latency p99, error rates, revenue impact for both policies; document decision and rationale |
| Add behavioral fingerprinting for proxy rotation detection | Presenter | May 20, 2026 | Implement detection of user-agent changes, request header variation, geolocation inconsistency, request timing patterns; define aggregate rate limit across detected same-attacker traffic |
| Add async replication SLA, per-IP debouncing, monitoring | Presenter | May 20, 2026 | SLA: 100ms p99 replication latency across all regional pairs; implement per-IP request debouncing (minimum time enforced between requests to different regions); add production monitoring with alerts and backpressure |
| Add per-API-key and per-user rate limits for authenticated requests | Presenter | June 1, 2026 | Implement per-user secondary limits (default 1000 tokens, 50/sec); apply more restrictive of IP limit and per-user limit per request; make overridable per-endpoint in YAML |

**Staging rollout impact:** Original target is "2 weeks from ~April 23" (≈ May 7). Per-user rate limiting revision is due June 1. **The presenter must either delay staging rollout until June 1 or phase revisions (land critical ones before staging, defer non-blocking ones to production phases).**

---

## Open questions for a later review
- Behavioral fingerprinting false-positive rate: how will the system distinguish legitimate users with header variation (e.g., different devices, networks) from attackers rotating proxies? Staging data needed.
- Per-IP request debouncing threshold: what minimum time between cross-region requests is sufficient to break the race condition without adding latency to legitimate multi-region traffic?
- Fail-open/fail-closed hybrid strategy: if chosen, what is the automated trigger to switch from fail-closed back to fail-open (e.g., Redis unavailability duration, error rate threshold)?
- Session-based rate limiting for unauthenticated traffic: defer to follow-up design; requires session identification at edge gateway.

---

## Risks the design explicitly acknowledges
- **Redis unavailability:** Design trades safety for uptime by failing open (allowing all traffic when Redis is down). **Status:** Deferred for measurement-backed decision (May 10).
- **Configuration drift:** YAML in repo may lag actual traffic patterns. **Status:** Presenter commits to quarterly review; no design change required.

---

## Summary for the presenter
Proceed with the revisions outlined above. All are substantive gaps rooted in prior incidents or viable attack mechanisms. Critical path:
1. **May 3:** Finalize multi-region architecture (local-only reads).
2. **May 10:** Complete fail-open/fail-closed measurement; decide strategy.
3. **May 20:** Deliver behavioral fingerprinting and async replication SLA.
4. **June 1:** Deliver per-user rate limiting.

Re-validate multi-region latency under the final architecture before staging rollout. The current claim of <10ms p99 added latency is valid only if eu-west-1 sidecars read from eu-west-1 Redis locally (not cross-region).
