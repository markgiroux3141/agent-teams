"""Steelman debate workflow: two extreme advocates + neutral team lead.

Two opinionated advocates (FOR / AGAINST) argue a proposition back-and-forth
for up to 20 turns, with early-exit if both sides start repeating themselves.
The team lead then produces a balanced synthesis.

Personas are extreme, rude, YouTube-commenter energy by design — the point
is to surface the strongest form of each side's argument under adversarial
pressure, not to produce polite commentary.

Default proposition is a live regulatory debate. Pass your own on the
command line for something different.

Usage:
    python examples/steelman.py
    python examples/steelman.py "Your proposition here."
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mat import Orchestrator, format_cost_summary, load_team_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOAL = (
    "Zero regulation on A.I. so we can get to ASI as soon as possible."
)


async def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set in .env.")
        return 1

    goal = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GOAL
    team = load_team_config(PROJECT_ROOT / "teams" / "steelman_team.yaml")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "runs" / run_id

    print(f"[run] id={run_id}  team={team.name}  proposition={goal!r}")
    print(f"[run] dir={run_dir}")
    print(f"[run] lead_model={team.lead.model}  "
          f"teammates={[f'{t.name}:{t.model}' for t in team.teammates]}")
    print(f"[run] max_iters={team.settings.max_loop_iterations}  "
          f"stall_timeout={team.settings.stall_timeout_seconds}s")

    orch = Orchestrator(team, goal, run_dir)
    output_path = await orch.run()

    print("\n=== Run complete ===")
    if output_path.exists():
        print(f"\nOUTPUT.md:\n{output_path.read_text(encoding='utf-8')}")
    else:
        print("(no OUTPUT.md — run interrupted or lead never finalized)")

    workspace = run_dir / "workspace"
    setup = workspace / "DONE_CRITERIA.md"
    if setup.exists():
        print(f"\nDONE_CRITERIA.md ({setup.stat().st_size} bytes) OK")

    debate = workspace / "debate"
    if debate.exists():
        turns = sorted(debate.glob("turn_*.md"))
        print(f"\nDebate turns produced ({len(turns)}):")
        for p in turns:
            print(f"  - {p.name}  ({p.stat().st_size} bytes)")

    print(f"\nCost summary:\n{format_cost_summary(run_dir)}")
    print(f"\nTrace: {run_dir / 'trace.jsonl'}")
    print(f"Tasks: {run_dir / 'tasks.jsonl'}")
    print(f"Summary: {run_dir / 'run_summary.json'}")
    print(f"Report:  {run_dir / 'report.html'}  (+ report.md)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
