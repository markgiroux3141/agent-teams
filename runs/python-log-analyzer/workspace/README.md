# logalyzer

A command-line log file analyser that counts lines by severity level, prints a
summary table, and lets you filter or search across one or more log files.

---

## Features

- **Level detection** — recognises `DEBUG`, `INFO`, `WARNING`, `ERROR`, and
  `CRITICAL` tokens (case-insensitive). Aliases are folded automatically:
  `WARN` → `WARNING`; `FATAL` / `SEVERE` → `CRITICAL`; `NOTICE` → `INFO`.
- **Summary table** — shows count, percentage share, and an ASCII bar chart for
  every level present in the input.
- **Multi-file support** — accepts any number of files; prints a per-file
  breakdown followed by aggregate totals when more than one file is given.
- **Level filter** (`--level`) — restricts matched output lines to a single
  severity level.
- **Keyword search** (`--search`) — case-insensitive substring filter across
  matched lines.
- **Show matched lines** (`--show-lines`) — prints the filtered/matched log
  lines (with line numbers) below the summary table.
- **Graceful error handling** — unreadable or missing files emit a diagnostic to
  stderr and return exit code 1; valid files in the same invocation are still
  processed.
- **stdlib only** — no third-party dependencies.

---

## Requirements

- Python **3.10** or later (uses the `X | Y` union type syntax).
- Standard library only (`argparse`, `re`, `collections`, `pathlib`).

---

## Installation

No packaging or install step is required. Clone the repository and run the
script directly:

```bash
git clone https://github.com/example/logalyzer.git
cd logalyzer
```

---

## Usage

```
python src/logalyzer.py [FILE ...] [--level LEVEL] [--search KEYWORD] [--show-lines]
```

### Positional arguments

| Argument | Description |
|----------|-------------|
| `FILE`   | One or more log files to analyse. |

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--level LEVEL` | `-l` | Filter displayed matched lines to this level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). The summary table always reflects the full file distribution. |
| `--search KEYWORD` | `-s` | Only display lines containing `KEYWORD` (case-insensitive substring match). |
| `--show-lines` | | Print matched lines with line numbers below the summary table. |

---

### Examples

**Basic summary of a single file**

```bash
$ python src/logalyzer.py /var/log/app.log

Level          Count   Share  Bar
---------------------------------
INFO              52   64.2%  #############.......
WARNING            8    9.9%  ##..................
ERROR             15   18.5%  ####................
CRITICAL           6    7.4%  #...................
---------------------------------
TOTAL             81
```

**Filter to ERROR lines and show them**

The summary table always shows the full file distribution so you keep the
context of how many errors there are relative to everything else.
`--level` (and `--search`) control which individual lines are printed below.

```bash
$ python src/logalyzer.py /var/log/app.log --level ERROR --show-lines

Level          Count   Share  Bar
---------------------------------
INFO              52   64.2%  #############.......
WARNING            8    9.9%  ##..................
ERROR             15   18.5%  ####................
CRITICAL           6    7.4%  #...................
---------------------------------
TOTAL             81

-- /var/log/app.log --
    42: 2024-03-01 09:11:03 ERROR  Failed to connect to DB (attempt 1)
    43: 2024-03-01 09:11:08 ERROR  Failed to connect to DB (attempt 2)
   ...
```

**Keyword search across multiple files**

```bash
$ python src/logalyzer.py /var/log/app.log /var/log/worker.log --search "timeout"

  app.log  (81 lines)
    ERROR          15
    CRITICAL        6

  worker.log  (205 lines)
    WARNING        11
    ERROR          28

Level          Count   Share  Bar
---------------------------------
INFO              98   34.3%  #######.............
WARNING           19    6.6%  #...................
ERROR             43   15.0%  ###.................
CRITICAL           8    2.8%  #...................
UNKNOWN          118   41.3%  ########............
---------------------------------
TOTAL            286

-- /var/log/app.log --
    19: 2024-03-01 08:55:12 ERROR  upstream read timeout after 30s
-- /var/log/worker.log --
    77: 2024-03-01 09:02:44 WARNING connection timeout; retrying
```

**Missing file — non-zero exit**

```bash
$ python src/logalyzer.py missing.log
[logalyzer] file not found: missing.log
$ echo $?
1
```

---

## Running the tests

The smoke test requires no external test runner:

```bash
cd src
python test_smoke.py
```

On success the final line is:

```
RESULT: all tests passed
```

Exit code is `0` on success, `1` if any test fails.

---

## Caveats

- **Encoding** — files are read as UTF-8; undecodable bytes are replaced rather
  than causing a hard failure.
- **First match wins** — only the first log-level token found on each line is
  used to classify that line. Lines with no recognised token are counted as
  `UNKNOWN`.
- **No streaming / tail mode** — the tool reads each file once from start to
  finish; it does not follow live log files.

---

## License

MIT
