"""M2 end-to-end demo: run the research-squad (3 teammates with dependencies).

Usage:
    python examples/research.py
    python examples/research.py "Brief on event sourcing vs traditional CRUD."
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Ensure stdout can render unicode (e.g. ✓, em-dashes) on Windows consoles.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mat import Orchestrator, format_cost_summary, load_team_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOAL = "Write a brief on the architectural tradeoffs of monoliths vs microservices."


async def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set in .env.")
        return 1

    goal = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GOAL

    team = load_team_config(PROJECT_ROOT / "teams" / "example_team.yaml")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "runs" / run_id

    print(f"[run] id={run_id}  team={team.name}  goal={goal!r}")
    print(f"[run] dir={run_dir}")

    orch = Orchestrator(team, goal, run_dir)
    output_path = await orch.run()

    print("\n=== Run complete ===")
    if output_path.exists():
        print(f"\nOUTPUT.md:\n{output_path.read_text(encoding='utf-8')}")
    else:
        print("(no OUTPUT.md produced — see trace.jsonl for diagnosis)")

    workspace = run_dir / "workspace"
    artifacts = sorted(p.name for p in workspace.glob("*.md") if p.name != "OUTPUT.md")
    if artifacts:
        print(f"\nIntermediate artifacts in {workspace}:")
        for name in artifacts:
            print(f"  - {name}")

    print(f"\nCost summary:\n{format_cost_summary(run_dir)}")
    print(f"\nTrace: {run_dir / 'trace.jsonl'}")
    print(f"Tasks: {run_dir / 'tasks.jsonl'}")
    print(f"Summary: {run_dir / 'run_summary.json'}")
    print(f"Report:  {run_dir / 'report.html'}  (+ report.md)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
