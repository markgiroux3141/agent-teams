# Code Review — v1

## Verdict: REVISE

## Summary
`logalyzer.py` is clean, well-structured, and hits almost every mark — stdlib-only,
no network, no shell injection, no `eval`, sensible error handling, and 195 lines.
`test_smoke.py` is genuinely useful: it verifies exact level counts, alias folding,
both filter modes, combined filtering, and CLI exit codes.  One blocking issue
prevents approval: the README's `--level` example documents summary-table behaviour
that the implementation does not actually produce.

---

## Blocking issues

- **README.md:88–102 vs logalyzer.py:66** — The `--level ERROR --show-lines` example
  in the README shows a summary table that contains *only* `ERROR  15  100.0%`.
  In the actual implementation, `counts[level] += 1` (line 66) executes for every
  line **before** the filter check at lines 68–74, so `counts` always reflects the
  full file distribution regardless of `--level`.  Running the same command against
  a real file will display all levels (INFO, WARNING, ERROR, CRITICAL, UNKNOWN) in
  the summary — not just ERROR at 100%.  Either:
  (a) fix the code so that `counts` is gated by `level_filter` (making the summary
      show only the requested level), or
  (b) correct the README example to match the actual all-levels summary output.
  As written, the deliverable ships with documentation that actively misleads users
  about a core feature.

---

## Non-blocking suggestions

- **logalyzer.py:43–47 and 81–87** — `show_lines: bool = False` is accepted by
  both `analyse_file` and `analyse_files` but is never read inside either function
  body.  The parameter is purely dead weight; remove it from both signatures (or
  use it — e.g. to skip populating `matched` when no display is needed).

- **logalyzer.py:168–171** — `main()` does not validate `args.level` against the
  known canonical set.  A user typo like `--level ERRO` produces an empty matched
  list with no diagnostic, silently appearing to succeed.  Consider checking
  `args.level.upper() in LEVELS_ORDER` and printing a helpful error before
  returning 1.

- **test_smoke.py:34** — `FAILURES: list[str] = []` is a module-level mutable list.
  Fine for this single-run script, but if `main_runner()` were ever called more than
  once in the same process (e.g. from a pytest harness), failures would accumulate
  across runs.  Moving the list inside `main_runner()` (or resetting it at entry)
  would make the function reentrant.

---

## Line count check

logalyzer.py: **195 lines** — PASS
