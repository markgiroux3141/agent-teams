# DONE CRITERIA — Python Utility Sprint

## Scope
A small Python utility. Domain is open — pick anything useful in under 200 lines.
Must include README.md and a smoke test that actually runs.

## Roster
- research_engineer: implements the Python utility. Owns workspace/src/.
- partnerships_analyst: writes workspace/README.md once src/ exists.
- code_reviewer: reviews every code artifact. Writes workspace/reviews/review_v<N>.md each round.

## Ground Rules
1. **Python only.** Prefer the standard library. A well-chosen third-party package is acceptable if the utility genuinely needs it.
2. **Offline-friendly.** The utility must NOT reach the network as part of its normal operation. Tests may exercise local files and sockets bound to loopback if needed, but the deliverable itself must be offline-friendly.
3. **Tests must actually run.** `python -m pytest` or `python test_smoke.py` — whatever the team picks, it must exit 0.
4. **README location:** workspace/README.md (NOT inside src/).
5. **Size limit:** under 200 lines total for the utility (smoke test excluded from the count).
6. **Code quality:** no hardcoded secrets, no shell injection, no `eval`, no unnecessary globals.

## Review Standard
Each review round produces workspace/reviews/review_v<N>.md with a top-line verdict:
  - **APPROVE** — ship it.
  - **REVISE** — list every blocking issue verbatim; author must address all before next review.

Cap: 4 review rounds max. If round 4 is still REVISE, finalize with REVISE_CAP_HIT.
