# Code Review — v2

## Verdict: APPROVE

## Summary
All three blocking and non-blocking issues raised in v1 have been addressed cleanly.
The README now accurately describes the summary-table behaviour for `--level`, level
validation has been added to `main()` with a helpful diagnostic, dead parameters are
gone, and the test suite was extended and made reentrant.  No new security concerns
were introduced; the utility remains stdlib-only, offline, and under 200 lines.

---

## Blocking issues

None.

---

## Non-blocking suggestions

- **README.md:117–121** — The per-file breakdown in the multi-file `--search "timeout"`
  example lists only `ERROR 15` and `CRITICAL 6` for `app.log  (81 lines)`.
  `print_summary`'s per-file loop (logalyzer.py:108–114) iterates all of `LEVELS_ORDER`
  and prints every non-zero level, so a real 81-line file carrying INFO/WARNING/DEBUG
  lines would also show those levels.  The example is slightly understated; consider
  updating it to show a full-level breakdown, or adding a note that the numbers are
  illustrative.

---

## Evolution

- **Fixed since v1:**
  - README `--level ERROR --show-lines` example now shows the full multi-level summary
    table, with added prose ("The summary table always shows the full file distribution…").
    Matches actual code behaviour. ✅
  - `show_lines: bool = False` dead parameter removed from both `analyse_file`
    (was line 47) and `analyse_files` (was line 84). Only live use — `args.show_lines`
    in `main()` line 190 — is correct. ✅
  - `main()` now validates `args.level` against `LEVELS_ORDER` (lines 170–173),
    printing `[logalyzer] unknown level … Valid: …` to stderr and returning 1. ✅
  - `FAILURES.clear()` added at the top of `main_runner()` (line 133), making the
    function reentrant. ✅
  - New `test_main_level_validation()` test (lines 123–129) exercises the error path
    (`"ERRO"` → exit 1) and the success path (`"ERROR"` → exit 0); wired into the
    runner at line 148. ✅

- **Still present from v1:** None.

- **New:** One minor README documentation note (per-file example, non-blocking above).

---

## Line count check

logalyzer.py: **197 lines** — PASS
