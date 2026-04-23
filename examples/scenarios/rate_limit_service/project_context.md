# Design review context — rate-limit service

**Under review:** Design doc for a new service, "RateGuard", intended
to protect the public API surface from abuse.

**Review goal:** Approve / revise / block. Substantiated critiques
only. The lead (Tech Lead) will triage critiques and dispatch a
rebuttal round to the presenter.

**Reviewers:**
- **presenter** — the design author, a senior backend engineer.
- **security** — a security reviewer who knows the company's prior
  incidents and the codebase's trust model.
- **perf** — a performance reviewer who knows the company's regional
  infrastructure and past scaling pain.

**Process:**
1. Presenter writes a summary of the design's claims + invariants.
2. Security and perf file critiques independently, substantiated by
   mechanism or prior incident.
3. Tech Lead triages — drops superficial critiques, flags
   substantiated ones + any cross-domain implications.
4. Presenter rebuts the substantiated critiques (accept / reject /
   defer per item).
5. Tech Lead issues verdict: approve, revise-with-specifics, or
   block-with-direction.

**Output:** `OUTPUT.md` — the verdict, the substantiated critiques
with resolutions, required revisions with owners.
