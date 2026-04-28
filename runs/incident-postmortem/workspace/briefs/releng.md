# Release engineering brief — incident 2026-04-20

## What I have

The deploy log for the checkout-service fleet, the release manifest
for the 14:01 deploy, and the change ticket.

## Deploy at 14:01:12 UTC

**Change ticket:** CHK-2417 — "Weekly dependency refresh + node
upgrade."

**Target:** checkout-service fleet, all regions, rolling deploy
(completed 14:01:12 → 14:03:45 across all pods).

**Release manifest (excerpt from `package.json` diff):**
```
- "express": "4.18.1",
+ "express": "4.18.3",
- "pg": "8.11.3",
+ "pg": "8.11.5",
- "user-session": "2.0.4",
+ "user-session": "2.1.0",
```

**Node runtime bump (in Dockerfile):** 18.17.1 → 18.18.2.

**Author's PR description (verbatim):** "Routine dependency refresh.
All patch-level updates; CI green. Node patch upgrade in base image.
Risk: low."

**My read of the manifest:** Three updates. Express and pg are
indeed patch-level (x.y.z→x.y.w). The node bump is a patch-level
(18.17.1→18.18.2 — 18.18 is actually a minor inside node's
convention, but commonly treated as a security patch).

The PR was reviewed and approved by one reviewer. CI passed. No
canary stage — the fleet gets rolled uniformly.

## My initial read

The deploy correlates with incident onset but it's all dependency
updates. The PR description calls it routine. Nothing stood out in
CI. The rollback worked, so whatever shipped is the issue, but the
manifest looks innocuous.

**I don't have release notes in-hand for the bumped libraries.** We
don't mandate reviewing upstream release notes for patch-level
bumps. If one of these was a behavior-breaking change masquerading
as a patch, I wouldn't have caught it.

## 14:35 rollback

Triggered manually at 14:35:07 UTC, completed at 14:37:50. Reverts
all three dependency bumps + node runtime. Recovery followed.

## What I don't know

- Whether any of the three dependency bumps carried a behavior
  change. Neither the PR description nor our CI checks for that.
- Whether any of these libraries are in hot paths that would
  explain session symptoms.
