"""M3 end-to-end demo: writer pauses mid-task to ask researcher a follow-up.

Expected flow:
  1. Lead creates t_001 (researcher → findings.md) and t_002 (writer → brief.md,
     depends on t_001). Researcher completes t_001.
  2. Writer is dispatched for t_002. findings.md lacks a specific figure, so
     writer sends a message to researcher and ends their turn WITHOUT calling
     update_task. Task stays in_progress.
  3. Orchestrator sees researcher has unread mail → reply-dispatch. Researcher
     reads, replies to writer, ends turn.
  4. Orchestrator sees writer has unread mail → reply-dispatch. Writer reads
     the figure, writes brief.md, calls update_task(completed).
  5. Lead finalizes.

Full exchange visible in trace.jsonl. The lead's inbox gets a CC of the
teammate-to-teammate traffic (cc_lead_on_messages: true).

Usage:
    python examples/messaging.py
    python examples/messaging.py "Brief on HTTP/2 vs HTTP/3 head-of-line blocking."
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
    "Write a brief on row-level vs page-level locking in relational databases. "
    "The brief must include at least one specific performance or contention figure."
)


async def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set in .env.")
        return 1

    goal = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GOAL

    team = load_team_config(PROJECT_ROOT / "teams" / "messaging_demo_team.yaml")

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

    messages_dir = run_dir / "messages"
    if messages_dir.exists():
        inboxes = sorted(messages_dir.glob("*.jsonl"))
        if inboxes:
            print(f"\nInboxes in {messages_dir}:")
            for inbox in inboxes:
                lines = [l for l in inbox.read_text(encoding="utf-8").splitlines() if l.strip()]
                print(f"  - {inbox.name}: {len(lines)} message(s)")

    print(f"\nCost summary:\n{format_cost_summary(run_dir)}")
    print(f"\nTrace: {run_dir / 'trace.jsonl'}")
    print(f"Tasks: {run_dir / 'tasks.jsonl'}")
    print(f"Summary: {run_dir / 'run_summary.json'}")
    print(f"Report:  {run_dir / 'report.html'}  (+ report.md)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
