"""Daily standup workflow: EM lead + 3 role-playing teammates.

Three teammates (backend, frontend, qa) read pre-seeded briefs and file
status updates in parallel. The Engineering Manager lead reads all updates
plus any teammate-to-teammate CC traffic, surfaces conflicts and unowned
blockers, dispatches directed follow-up tasks, and synthesizes.

Scenarios are bundles: a directory with `project_context.md` and
`briefs/<role>.md` per teammate. The launcher copies them into the run's
workspace before the orchestrator starts.

Usage:
    python examples/standup.py
    python examples/standup.py --scenario examples/scenarios/checkout_refactor
    python examples/standup.py --scenario path/to/my/scenario --goal "Mon sprint sync"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mat import Orchestrator, format_cost_summary, load_team_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCENARIO = PROJECT_ROOT / "examples" / "scenarios" / "checkout_refactor"
DEFAULT_GOAL = (
    "Run today's standup. Collect status from every teammate, surface "
    "conflicts and unowned blockers explicitly, dispatch targeted "
    "follow-ups, and deliver a synthesis with named owners for every "
    "open item."
)


def seed_workspace(scenario: Path, workspace: Path) -> list[str]:
    """Copy scenario files into workspace. Returns list of relative paths copied."""
    scenario = scenario.resolve()
    if not scenario.is_dir():
        raise FileNotFoundError(f"Scenario directory not found: {scenario}")

    context_src = scenario / "project_context.md"
    if not context_src.is_file():
        raise FileNotFoundError(f"Missing {context_src}")
    briefs_dir = scenario / "briefs"
    if not briefs_dir.is_dir():
        raise FileNotFoundError(f"Missing {briefs_dir}")

    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "briefs").mkdir(parents=True, exist_ok=True)
    (workspace / "updates").mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    shutil.copy(context_src, workspace / "project_context.md")
    copied.append("project_context.md")
    for brief in sorted(briefs_dir.glob("*.md")):
        shutil.copy(brief, workspace / "briefs" / brief.name)
        copied.append(f"briefs/{brief.name}")
    return copied


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run a multi-agent daily standup.")
    parser.add_argument(
        "--scenario",
        type=Path,
        default=DEFAULT_SCENARIO,
        help="Path to a scenario directory (project_context.md + briefs/).",
    )
    parser.add_argument(
        "--goal",
        type=str,
        default=DEFAULT_GOAL,
        help="Override the top-level goal string handed to the lead.",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set in .env.")
        return 1

    team = load_team_config(PROJECT_ROOT / "teams" / "standup_team.yaml")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = PROJECT_ROOT / "runs" / run_id
    workspace = run_dir / "workspace"

    try:
        seeded = seed_workspace(args.scenario, workspace)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    print(f"[run] id={run_id}  team={team.name}")
    print(f"[run] scenario={args.scenario}")
    print(f"[run] seeded: {', '.join(seeded)}")
    print(f"[run] dir={run_dir}")
    print(f"[run] lead_model={team.lead.model}  "
          f"teammates={[f'{t.name}:{t.model}' for t in team.teammates]}")
    print(f"[run] max_iters={team.settings.max_loop_iterations}  "
          f"stall_timeout={team.settings.stall_timeout_seconds}s")

    orch = Orchestrator(team, args.goal, run_dir)
    output_path = await orch.run()

    print("\n=== Run complete ===")
    if output_path.exists():
        print(f"\nOUTPUT.md:\n{output_path.read_text(encoding='utf-8')}")
    else:
        print("(no OUTPUT.md — run interrupted or lead never finalized)")

    agenda = workspace / "DONE_CRITERIA.md"
    if agenda.exists():
        print(f"\nDONE_CRITERIA.md ({agenda.stat().st_size} bytes) OK")

    updates = workspace / "updates"
    if updates.exists():
        files = sorted(updates.glob("*.md"))
        print(f"\nStatus updates produced ({len(files)}):")
        for p in files:
            print(f"  - {p.name}  ({p.stat().st_size} bytes)")

    print(f"\nCost summary:\n{format_cost_summary(run_dir)}")
    print(f"\nTrace: {run_dir / 'trace.jsonl'}")
    print(f"Tasks: {run_dir / 'tasks.jsonl'}")
    print(f"Summary: {run_dir / 'run_summary.json'}")
    print(f"Report:  {run_dir / 'report.html'}  (+ report.md)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
