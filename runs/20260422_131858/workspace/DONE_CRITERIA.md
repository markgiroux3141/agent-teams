# DONE_CRITERIA: stats.py weekend demo

This is a **weekend prototype** — not production code. Speed and functionality over polish.

## Runnable
- [x] File: workspace/src/stats.py
- [x] Invocation: `python stats.py <file>` with a CSV file path
- [x] No external dependencies (stdlib only)

## Output
When run on a file, prints exactly these four statistics (on stdout, clear format):
- **count**: number of values
- **mean**: arithmetic mean
- **median**: middle value (or average of two middle for even count)
- **population stddev**: population standard deviation (divide by N, not N-1)

## Edge Cases
- [x] Empty file (0 lines): print count=0, handle gracefully (mean/median/stddev as 0 or "N/A" acceptable)
- [x] Single value: count=1, mean=value, median=value, stddev=0
- [x] File not found or read error: print clear error message, exit cleanly

## Out of Scope (explicitly NOT required)
- Tests
- Error recovery for malformed numbers (simple int() parsing OK, crashes on non-numeric input acceptable)
- Command-line flags or options
- Prettified output formatting
- Performance optimization
- Type hints or docstrings

## Stopping Yardstick
Code is done when:
- All four stats print correctly for typical input (5+ numbers, 1 number, empty file)
- Runs with `python stats.py <file>` without external deps
- Zero CRITICAL issues remain
- Zero IMPORTANT issues remain

## Quality Targets
- NICE-TO-HAVE: readable code (clear variable names)
- NICE-TO-HAVE: comments if logic is non-obvious
- NOT A GOAL: enterprise patterns, tests, or advanced features
