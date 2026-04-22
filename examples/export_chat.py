"""Export a debate run as a single, readable CHAT_HISTORY.md.

Reads workspace/DONE_CRITERIA.md (for the proposition) and every
workspace/debate/turn_*.md, concatenates them into
workspace/CHAT_HISTORY.md in the run dir.

Usage:
  python examples/export_chat.py runs/20260422_154916
  python examples/export_chat.py runs/20260422_154916 runs/20260422_160700_inlined
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def extract_proposition(done_criteria_text: str) -> str:
    m = re.search(r'"([^"]{10,})"', done_criteria_text)
    return m.group(1) if m else "(proposition not found in DONE_CRITERIA.md)"


def build_chat_history(run_dir: Path) -> str:
    workspace = run_dir / "workspace"
    debate = workspace / "debate"
    if not debate.exists():
        return f"(no debate/ directory in {run_dir})"

    done = workspace / "DONE_CRITERIA.md"
    proposition = (
        extract_proposition(done.read_text(encoding="utf-8"))
        if done.exists()
        else "(DONE_CRITERIA.md missing)"
    )

    lines = [
        f"# Debate chat history — {run_dir.name}",
        "",
        "## Proposition",
        "",
        f"> {proposition}",
        "",
        "---",
        "",
    ]

    for p in sorted(debate.glob("turn_*.md")):
        body = p.read_text(encoding="utf-8").strip()
        lines.append(body)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python examples/export_chat.py <run_dir> [<run_dir> ...]")
        return 1
    for arg in sys.argv[1:]:
        run_dir = Path(arg).resolve()
        if not run_dir.exists():
            print(f"ERROR: {run_dir} does not exist")
            return 1
        out = run_dir / "workspace" / "CHAT_HISTORY.md"
        out.write_text(build_chat_history(run_dir), encoding="utf-8")
        print(f"Wrote {out}  ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
