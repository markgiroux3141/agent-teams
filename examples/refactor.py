"""M5 capstone demo: build-critique-refactor loop with 3 teammates.

Exercises the full stack: M2 dependencies (each round depends on the prior),
M3 messaging (refactor_dev can ping critic to clarify items; lead is CC'd),
M4 stall timeouts + cost tracking, and M5 write_scratchpad (lead sets
DONE_CRITERIA.md before any code is written).

Default goal is a small, concrete CLI that haiku can actually build. Pass
your own goal on the command line for something different.

Usage:
    python examples/refactor.py
    python examples/refactor.py "A Python CLI that ..."
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
    "Build a browser-only Three.js flight simulator demo under workspace/src/. "
    "Deliverables: index.html that loads Three.js from a CDN, plus whatever "
    "JS files you need. Features: a procedurally generated terrain (can be "
    "a heightmap or a simple hilly plane), a simple plane model (a box with "
    "wings is fine), WASD or arrow-key flight controls, third-person chase "
    "camera, sky/fog for atmosphere. This is a weekend demo — no build "
    "step, no bundler, no npm, no tests. Opening index.html in a browser "
    "must produce a flyable scene. Do NOT try to run it with Bash; browsers "
    "only. The critic will review the code statically."
)


async def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set in .env.")
        return 1

    goal = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GOAL
    team = load_team_config(PROJECT_ROOT / "teams" / "refactor_loop_team.yaml")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "runs" / run_id

    print(f"[run] id={run_id}  team={team.name}  goal={goal!r}")
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
    done_criteria = workspace / "DONE_CRITERIA.md"
    if done_criteria.exists():
        print(f"\nDONE_CRITERIA.md ({done_criteria.stat().st_size} bytes) ✓")

    src = workspace / "src"
    if src.exists():
        print(f"\nFinal src/ tree:")
        for p in sorted(src.rglob("*")):
            if p.is_file():
                rel = p.relative_to(workspace)
                print(f"  {rel}  ({p.stat().st_size} bytes)")

    critiques = workspace / "critiques"
    if critiques.exists():
        print(f"\nCritique rounds produced:")
        for p in sorted(critiques.glob("critique_v*.md")):
            print(f"  - {p.name}  ({p.stat().st_size} bytes)")

    print(f"\nCost summary:\n{format_cost_summary(run_dir)}")
    print(f"\nTrace: {run_dir / 'trace.jsonl'}")
    print(f"Tasks: {run_dir / 'tasks.jsonl'}")
    print(f"Summary: {run_dir / 'run_summary.json'}")
    print(f"Report:  {run_dir / 'report.html'}  (+ report.md)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
