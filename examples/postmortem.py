"""Incident postmortem workflow: IC lead + 4 domain investigators.

Four teammates (sre, observability, releng, support) read pre-seeded
briefs of partial evidence from an incident window, file findings in
parallel, and exchange peer messages about cross-domain implications.
The IC lead reads all findings + any peer CC traffic, identifies
contradictions / convergences / gaps, dispatches directed follow-ups
to force triangulation, and synthesizes a root-cause hypothesis with
remediation owners.

The default scenario ("checkout_outage") is designed so the root cause
is NOT recoverable from any single domain's findings — it requires a
join between releng's deploy manifest (a version bump misdescribed as
"patch-level") and support's "kicked out after a few minutes" pattern,
with observability's cache-hit drop corroborating.

Usage:
    python examples/postmortem.py
    python examples/postmortem.py --scenario examples/scenarios/checkout_outage
    python examples/postmortem.py --scenario path/to/my/scenario --goal "Custom IC framing"
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
DEFAULT_SCENARIO = PROJECT_ROOT / "examples" / "scenarios" / "checkout_outage"
DEFAULT_GOAL = (
    "Run the incident postmortem. Pool evidence from all four investigators, "
    "force cross-domain triangulation on contradictions and gaps, converge on "
    "a root-cause hypothesis supported by a specific join of evidence, and "
    "deliver remediation with named owners."
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
    (workspace / "findings").mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    shutil.copy(context_src, workspace / "project_context.md")
    copied.append("project_context.md")
    for brief in sorted(briefs_dir.glob("*.md")):
        shutil.copy(brief, workspace / "briefs" / brief.name)
        copied.append(f"briefs/{brief.name}")
    return copied


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run a multi-agent incident postmortem.")
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

    team = load_team_config(PROJECT_ROOT / "teams" / "postmortem_team.yaml")

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

    findings = workspace / "findings"
    if findings.exists():
        files = sorted(findings.glob("*.md"))
        print(f"\nFindings produced ({len(files)}):")
        for p in files:
            print(f"  - {p.name}  ({p.stat().st_size} bytes)")

    print(f"\nCost summary:\n{format_cost_summary(run_dir)}")
    print(f"\nTrace: {run_dir / 'trace.jsonl'}")
    print(f"Tasks: {run_dir / 'tasks.jsonl'}")
    print(f"Summary: {run_dir / 'run_summary.json'}")
    print(f"Report:  {run_dir / 'report.html'}  (+ report.md, sequence.md, playback.html, stage.html)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
