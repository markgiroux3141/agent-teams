# Security reviewer brief

## Your standing context for this team

You've reviewed 3 prior rate-limit-ish designs on this codebase over
the past 18 months. The pattern: engineering tends to over-trust
network-layer identifiers (IP, user-agent) and under-model realistic
abuse. Your job is to make sure we don't ship that mistake again.

## Known company incidents that are relevant

- **Q4 2024:** Coupon-code abuse — credential-stuffing-style attack
  on our coupon endpoint rotated source IPs via a pool of residential
  proxies. IP-based throttling was in place; it rate-limited each IP
  but the attacker had thousands of IPs. Net effect: the rate limit
  didn't help. We had to ship CAPTCHA + per-account limits on top.

- **Q1 2025:** Corporate customer complaint — large B2B customer
  (sharing a single egress NAT across ~2000 employees) was getting
  their normal traffic rate-limited because all requests looked
  like they came from one IP. Took two weeks to tune, unhappy
  account manager.

- **Q3 2024:** Mobile carrier NAT — same problem, different shape.
  Mobile users on one carrier share a small pool of egress IPs;
  they got rate-limited harder than web users on residential
  connections, by accident.

## Things to explicitly check on this review

- Any assumption that "IP == caller" is load-bearing for safety.
- Any assumption about attacker cost that doesn't price in botnets
  or proxy rotation.
- The fail-open policy on Redis unavailability — is that consistent
  with what we're promising to protect against?

## What you should NOT critique

- Performance (that's perf's job).
- Aesthetic or code-style concerns — irrelevant to design review.
- The Lua script implementation itself — out of scope for design.
