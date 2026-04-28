"""
test_smoke.py — Smoke test for logalyzer.py
Runs without network access, pytest, or any third-party package.
Exit 0 on success, non-zero on any failure.
"""

import sys
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

# ── Ensure sibling module is importable regardless of CWD ────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from logalyzer import (
    analyse_file,
    classify_line,
    main,
)

SAMPLE_LOG = textwrap.dedent("""\
    2024-01-01 08:00:00 INFO  Server started
    2024-01-01 08:01:00 INFO  Listening on :8080
    2024-01-01 08:05:00 DEBUG Loaded config from /etc/app.conf
    2024-01-01 08:10:00 WARNING High memory usage: 82%
    2024-01-01 08:11:00 ERROR  Failed to connect to DB (attempt 1)
    2024-01-01 08:11:05 ERROR  Failed to connect to DB (attempt 2)
    2024-01-01 08:11:10 CRITICAL DB connection pool exhausted
    2024-01-01 08:12:00 INFO  Falling back to read-only mode
    plain line with no level token
""")

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        msg = f"  FAIL  {name}" + (f": {detail}" if detail else "")
        print(msg)
        FAILURES.append(msg)


# ── Test: classify_line ───────────────────────────────────────────────────────

def test_classify_line() -> None:
    print("\n[classify_line]")
    cases = [
        ("2024-01-01 INFO  booting",           "INFO"),
        ("WARN: disk space low",               "WARNING"),
        ("FATAL: out of memory",               "CRITICAL"),
        ("SEVERE unhandled exception",         "CRITICAL"),
        ("NOTICE: config reloaded",            "INFO"),
        ("nothing special here",               "UNKNOWN"),
        ("[ERROR] write failed",               "ERROR"),
        ("2024-01-01 DEBUG payload dump",      "DEBUG"),
    ]
    for line, expected in cases:
        got = classify_line(line)
        check(f"classify({line[:40]!r})", got == expected, f"got {got!r}")


# ── Test: analyse_file with a temp log ───────────────────────────────────────

def test_analyse_file(tmp_log: Path) -> None:
    print("\n[analyse_file — no filter]")
    counts, matched = analyse_file(tmp_log)

    check("INFO count == 3",     counts.get("INFO", 0) == 3,     str(counts))
    check("WARNING count == 1",  counts.get("WARNING", 0) == 1,  str(counts))
    check("ERROR count == 2",    counts.get("ERROR", 0) == 2,    str(counts))
    check("CRITICAL count == 1", counts.get("CRITICAL", 0) == 1, str(counts))
    check("DEBUG count == 1",    counts.get("DEBUG", 0) == 1,    str(counts))
    check("UNKNOWN count == 1",  counts.get("UNKNOWN", 0) == 1,  str(counts))
    check("no matches without filter", matched == [], str(matched[:2]))


def test_analyse_file_level_filter(tmp_log: Path) -> None:
    print("\n[analyse_file — level filter ERROR]")
    counts, matched = analyse_file(tmp_log, level_filter="ERROR")
    check("matched lines == 2", len(matched) == 2, str(len(matched)))
    check("all matched are ERROR lines",
          all("ERROR" in line for _, line in matched),
          str(matched))


def test_analyse_file_keyword(tmp_log: Path) -> None:
    print("\n[analyse_file — keyword 'DB']")
    counts, matched = analyse_file(tmp_log, keyword="DB")
    check("matched lines == 3", len(matched) == 3, str(len(matched)))


def test_analyse_file_level_and_keyword(tmp_log: Path) -> None:
    print("\n[analyse_file — ERROR + keyword 'attempt']")
    counts, matched = analyse_file(tmp_log, level_filter="ERROR", keyword="attempt")
    check("matched lines == 2", len(matched) == 2, str(len(matched)))


# ── Test: main() CLI interface ────────────────────────────────────────────────

def test_main_exit_codes(tmp_log: Path) -> None:
    print("\n[main — exit codes]")
    rc_ok = main([str(tmp_log)])
    check("exit 0 on valid file", rc_ok == 0, str(rc_ok))

    rc_missing = main(["__nonexistent__.log"])
    check("exit 1 on missing file", rc_missing == 1, str(rc_missing))


def test_main_with_flags(tmp_log: Path) -> None:
    print("\n[main — flags]")
    rc = main([str(tmp_log), "--level", "ERROR", "--show-lines"])
    check("exit 0 with --level --show-lines", rc == 0, str(rc))

    rc2 = main([str(tmp_log), "--search", "memory"])
    check("exit 0 with --search", rc2 == 0, str(rc2))


# ── Runner ────────────────────────────────────────────────────────────────────

def test_main_level_validation(tmp_log: Path) -> None:
    print("\n[main — --level validation]")
    rc_bad = main([str(tmp_log), "--level", "ERRO"])
    check("exit 1 on unknown level", rc_bad == 1, str(rc_bad))

    rc_good = main([str(tmp_log), "--level", "ERROR"])
    check("exit 0 on valid level", rc_good == 0, str(rc_good))


def main_runner() -> int:
    FAILURES.clear()  # reset so multiple calls in the same process don't accumulate
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".log", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(SAMPLE_LOG)
        tmp_path = Path(fh.name)

    try:
        test_classify_line()
        test_analyse_file(tmp_path)
        test_analyse_file_level_filter(tmp_path)
        test_analyse_file_keyword(tmp_path)
        test_analyse_file_level_and_keyword(tmp_path)
        test_main_exit_codes(tmp_path)
        test_main_with_flags(tmp_path)
        test_main_level_validation(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    print("\n" + "-" * 40)
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} failure(s)")
        for f in FAILURES:
            print(f)
        return 1

    print("RESULT: all tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main_runner())
