"""Recipes-website workflow: deliberate → lock a SPEC → build in parallel.

Four-role team (backend, frontend, ux, recipe writer) + tech-lead / PM.
A deliberately vague ask ("build a recipes website") is handed to the
team. They run two rounds of negotiation, backend writes a SPEC.md that
every teammate builds against, then all four build tasks dispatch in
parallel WITHOUT further cross-team messaging. The lead verifies the
produced files and writes the build report.

Success looks like: `workspace/index.html` opens in a browser and shows
a recipes list with styling and actual content.

Usage:
    python examples/recipes.py
    python examples/recipes.py --scenario examples/scenarios/recipes_site
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
DEFAULT_SCENARIO = PROJECT_ROOT / "examples" / "scenarios" / "recipes_site"
DEFAULT_GOAL = (
    "Ship a recipes website. Take the vague brief through two rounds of "
    "team deliberation, produce a SPEC.md that pins every cross-team "
    "contract, then dispatch parallel build tasks with no further "
    "coordination. Verify the produced files form a working static site."
)


def seed_workspace(scenario: Path, workspace: Path) -> list[str]:
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
    (workspace / "proposals").mkdir(parents=True, exist_ok=True)
    # All runtime website files (HTML/CSS/JS/data) live under src/ so
    # they're separate from planning docs (SPEC, proposals, briefs,
    # OUTPUT) at the workspace root.
    (workspace / "src").mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    shutil.copy(context_src, workspace / "project_context.md")
    copied.append("project_context.md")
    for brief in sorted(briefs_dir.glob("*.md")):
        shutil.copy(brief, workspace / "briefs" / brief.name)
        copied.append(f"briefs/{brief.name}")
    return copied


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run a multi-agent recipes-website build.")
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

    team = load_team_config(PROJECT_ROOT / "teams" / "recipes_team.yaml")

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

    spec = workspace / "SPEC.md"
    if spec.exists():
        print(f"\nSPEC.md ({spec.stat().st_size} bytes) OK")

    print("\nWorkspace artifacts:")
    # Planning artifacts at workspace root + proposals/
    for folder in (".", "proposals"):
        d = workspace if folder == "." else workspace / folder
        if not d.exists():
            continue
        prefix = "" if folder == "." else f"{folder}/"
        for p in sorted(d.iterdir()):
            if p.is_file() and p.name not in ("project_context.md",):
                print(f"  - {prefix}{p.name}  ({p.stat().st_size} bytes)")
    # Runtime website files under src/
    src_dir = workspace / "src"
    if src_dir.exists():
        print("  src/ (runtime website):")
        for p in sorted(src_dir.rglob("*")):
            if p.is_file():
                rel = p.relative_to(src_dir)
                print(f"    - {rel}  ({p.stat().st_size} bytes)")

    print(f"\nCost summary:\n{format_cost_summary(run_dir)}")
    print(f"\nTrace: {run_dir / 'trace.jsonl'}")
    print(f"Tasks: {run_dir / 'tasks.jsonl'}")
    print(f"Summary: {run_dir / 'run_summary.json'}")
    print(f"Report:  {run_dir / 'report.html'}  (+ report.md, sequence.md, playback.html, stage.html)")

    src_dir = workspace / "src"
    spec = workspace / "SPEC.md"
    if src_dir.exists() and any(src_dir.iterdir()):
        print(f"\n→ Produced source files are in: {src_dir}")
        if spec.exists():
            print(f"→ See SPEC.md for the chosen stack and how to run it: {spec}")
        print(f"→ Lead's build report (OUTPUT.md) summarizes what was built and how to use it.")
    else:
        print(f"\n(No source files produced under src/ — inspect SPEC.md and the build-task"
              f" notes for why.)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
