# Daily Standup — Wednesday, 2026-04-22

**Project:** Checkout refactor from legacy monolith to new payments API v2.  
**Context:** Day 3 of 5. Ship Friday 2026-04-24. Feature-flagged rollout, ramp to 100% Monday if metrics hold. PM is out sick until Thursday. Payments team's legacy API goes read-only Saturday. Compliance needs clean audit log from Monday onward.

---

## Roster

- **backend**: Backend engineer on payments API v2. Owns server-side contracts and infrastructure.
- **frontend**: Frontend engineer rewriting checkout flow on the new API. Owns React checkout component and feature flag integration.
- **qa**: QA engineer on regression suite and staging environment. Owns test coverage and environment health.

---

## Required status format

Each teammate must write their update to `updates/<role>.md` using this format:

```
## Yesterday
- [bullet] What did you ship or complete?

## Today
- [bullet] What are you building today?

## Blockers
- [bullet] What's stuck? (Write "needs owner" if unclear who owns it)

## Questions for the team
- [bullet] What do you need from someone else?
```

---

## Cross-team concern rule

**Critical:** If your update mentions something you believe another teammate owns, or a handoff, or a conflicting assumption — **flag it immediately via `send_message` before marking your task complete.** 

Examples:
- "Backend, I'm blocked waiting for the coupon endpoint. Can you confirm it exists in v2.yaml?"
- "Frontend, QA here — I saw you built for the flag path, but the release doc says cutover. Which one are we shipping?"
- "QA, the staging seed is broken. Backend or infra — who owns `infra/seed/`?"

The lead is CC'd automatically and will use your flags to dispatch follow-ups.

---

## Standup goal

Collect status in parallel, surface all conflicts explicitly, own every blocker with a named person, and deliver a synthesis of what ships Friday.
