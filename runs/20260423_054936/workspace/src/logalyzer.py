"""
logalyzer.py — Log file analyser
Counts lines by log level, shows a summary table, and filters by level or keyword.
Usage:
    python logalyzer.py [FILE ...] [--level LEVEL] [--search KEYWORD] [--show-lines]
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

# Match log-level tokens; canonical map folds aliases (WARN->WARNING, FATAL->CRITICAL, …)
_LEVEL_RE = re.compile(
    r"\b(DEBUG|INFO|NOTICE|WARNING|WARN|ERROR|CRITICAL|FATAL|SEVERE)\b",
    re.IGNORECASE,
)

_CANONICAL: dict[str, str] = {
    "DEBUG":    "DEBUG",
    "INFO":     "INFO",
    "NOTICE":   "INFO",
    "WARNING":  "WARNING",
    "WARN":     "WARNING",
    "ERROR":    "ERROR",
    "CRITICAL": "CRITICAL",
    "FATAL":    "CRITICAL",
    "SEVERE":   "CRITICAL",
}

LEVELS_ORDER = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "UNKNOWN"]


def classify_line(line: str) -> str:
    """Return the canonical log level for *line*, or 'UNKNOWN'."""
    m = _LEVEL_RE.search(line)
    if m:
        return _CANONICAL.get(m.group(1).upper(), "UNKNOWN")
    return "UNKNOWN"


def analyse_file(
    path: Path,
    level_filter: str | None = None,
    keyword: str | None = None,
) -> tuple[Counter, list[tuple[int, str]]]:
    """
    Parse *path* and return (counter, matched_lines).

    counter        — counts per canonical level (all lines, no filter applied).
    matched_lines  — (lineno, text) pairs that pass level_filter and keyword.
    """
    counts: Counter = Counter()
    matched: list[tuple[int, str]] = []
    kw_re = re.compile(re.escape(keyword), re.IGNORECASE) if keyword else None
    lf = level_filter.upper() if level_filter else None
    active_filter = lf is not None or kw_re is not None

    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for lineno, raw in enumerate(fh, 1):
                line = raw.rstrip("\n")
                level = classify_line(line)
                counts[level] += 1

                if not active_filter:
                    continue
                if lf and level != lf:
                    continue
                if kw_re and not kw_re.search(line):
                    continue
                matched.append((lineno, line))
    except OSError as exc:
        print(f"[logalyzer] cannot read {path}: {exc}", file=sys.stderr)

    return counts, matched


def analyse_files(
    paths: list[Path],
    level_filter: str | None = None,
    keyword: str | None = None,
) -> dict[Path, tuple[Counter, list[tuple[int, str]]]]:
    return {p: analyse_file(p, level_filter, keyword) for p in paths}


def _bar(count: int, total: int, width: int = 20) -> str:
    if total == 0:
        return " " * width
    filled = round(count / total * width)
    return "#" * filled + "." * (width - filled)


def print_summary(results: dict[Path, tuple[Counter, list]]) -> None:
    # Aggregate totals across all files
    totals: Counter = Counter()
    for counts, _ in results.values():
        totals.update(counts)

    grand_total = sum(totals.values())
    if grand_total == 0:
        print("(no lines processed)")
        return

    # Per-file header when multiple files
    if len(results) > 1:
        for path, (counts, _) in results.items():
            file_total = sum(counts.values())
            print(f"\n  {path.name}  ({file_total} lines)")
            for lvl in LEVELS_ORDER:
                n = counts.get(lvl, 0)
                if n:
                    print(f"    {lvl:<10} {n:>6}")

    # Summary table
    header = f"{'Level':<12} {'Count':>7}  {'Share':>6}  {'Bar'}"
    sep = "-" * len(header)
    print()
    print(header)
    print(sep)
    for lvl in LEVELS_ORDER:
        n = totals.get(lvl, 0)
        if n == 0:
            continue
        pct = n / grand_total * 100
        bar = _bar(n, grand_total)
        print(f"{lvl:<12} {n:>7}  {pct:>5.1f}%  {bar}")
    print(sep)
    print(f"{'TOTAL':<12} {grand_total:>7}")


def print_matches(results: dict[Path, tuple[Counter, list[tuple[int, str]]]]) -> None:
    for path, (_, matched) in results.items():
        if not matched:
            continue
        print(f"\n-- {path} --")
        for lineno, line in matched:
            print(f"  {lineno:>6}: {line}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="logalyzer",
        description="Analyse log files: count by level, filter, and search.",
    )
    p.add_argument("files", nargs="+", metavar="FILE", help="Log file(s) to analyse")
    p.add_argument(
        "--level", "-l",
        metavar="LEVEL",
        help="Filter output lines to this level (DEBUG/INFO/WARNING/ERROR/CRITICAL)",
    )
    p.add_argument(
        "--search", "-s",
        metavar="KEYWORD",
        help="Only show lines containing KEYWORD (case-insensitive)",
    )
    p.add_argument(
        "--show-lines",
        action="store_true",
        help="Print matched lines below the summary table",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.level and args.level.upper() not in LEVELS_ORDER:
        valid = ", ".join(LEVELS_ORDER)
        print(f"[logalyzer] unknown level {args.level!r}. Valid: {valid}", file=sys.stderr)
        return 1

    paths = [Path(f) for f in args.files]
    missing = [p for p in paths if not p.exists()]
    if missing:
        for m in missing:
            print(f"[logalyzer] file not found: {m}", file=sys.stderr)
        return 1

    results = analyse_files(
        paths,
        level_filter=args.level,
        keyword=args.search,
    )

    print_summary(results)

    if args.show_lines or args.level or args.search:
        print_matches(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
