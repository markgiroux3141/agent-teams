"""Replay harness: rebuild coordination state from a trace.jsonl without the API.

Reads the `tool_use` events in order and dispatches the equivalent `TaskStore`
/ `MessageBus` operations into a fresh state directory. This validates that
traces capture enough information to reproduce the observable coordination
effects — useful for regression testing orchestrator logic without burning
tokens.

What's NOT replayed: built-in tool effects (`Read`, `Write`, `Edit`, `Bash`)
on the workspace. Those depend on model reasoning that we don't record. The
replay covers the coordination surface (task board, messaging, finalize),
which is what the orchestrator actually makes decisions on.

Note on task id determinism: `TaskStore.create_task` assigns ids from a
sequential counter (`t_001`, `t_002`, ...), so replaying create_task calls
in the same order produces the same ids — no id remapping needed."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from mat.state.message_bus import MessageBus
from mat.state.task_store import TaskStore, Task


@dataclass
class ReplayResult:
    tasks: list[Task]
    inbox_counts: dict[str, int]
    finalized: str | None
    cc_agent: str | None
    tool_use_count: int = 0
    coord_count: int = 0
    unknown_tools: list[str] = field(default_factory=list)


_COORD_PREFIX = "mcp__coord__"


def replay_trace(trace_path: Path, out_dir: Path) -> ReplayResult:
    trace_path = Path(trace_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cc_agent = _read_cc_agent(trace_path)

    task_store = TaskStore(out_dir / "tasks.jsonl")
    message_bus = MessageBus(out_dir / "messages", cc_agent=cc_agent)
    finalized: str | None = None

    tool_use_count = 0
    coord_count = 0
    unknown_tools: list[str] = []

    with trace_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            evt = json.loads(line)
            if evt.get("event") != "tool_use":
                continue
            tool_use_count += 1
            name = evt.get("name", "")
            if not name.startswith(_COORD_PREFIX):
                continue
            coord_count += 1
            op = name[len(_COORD_PREFIX):]
            agent = evt.get("agent", "")
            args = evt.get("input", {}) or {}

            if op == "create_task":
                task_store.create_task(
                    title=args.get("title", ""),
                    description=args.get("description", ""),
                    dependencies=args.get("dependencies") or [],
                )
            elif op == "assign_task":
                task_store.assign_task(args["task_id"], args["agent"])
            elif op == "claim_task":
                task_store.claim_task(args["task_id"], agent)
            elif op == "update_task":
                task_store.update_status(
                    task_id=args["task_id"],
                    status=args["status"],
                    note=args.get("note"),
                    result_ref=args.get("result_ref"),
                )
            elif op == "send_message":
                message_bus.send(
                    to=args["to"],
                    sender=agent,
                    content=args.get("content", ""),
                )
            elif op == "finalize":
                finalized = args.get("synthesis", "")
            elif op in {"read_messages", "list_tasks", "get_teammate_info"}:
                # Read-only on coord state, no replay needed.
                pass
            elif op == "write_scratchpad":
                # Mutates the workspace (file write), not coord state. Replay
                # rebuilds coord state only; skip silently.
                pass
            else:
                unknown_tools.append(op)

    inbox_counts = {}
    messages_dir = out_dir / "messages"
    if messages_dir.exists():
        for inbox in messages_dir.glob("*.jsonl"):
            with inbox.open(encoding="utf-8") as f:
                inbox_counts[inbox.stem] = sum(1 for line in f if line.strip())

    return ReplayResult(
        tasks=task_store.list_tasks(),
        inbox_counts=inbox_counts,
        finalized=finalized,
        cc_agent=cc_agent,
        tool_use_count=tool_use_count,
        coord_count=coord_count,
        unknown_tools=unknown_tools,
    )


def _read_cc_agent(trace_path: Path) -> str | None:
    """The cc_agent setting lives on the run_start event. Honor it during
    replay so CC rows land in the same inbox as the original run."""
    with Path(trace_path).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            evt = json.loads(line)
            if evt.get("event") == "run_start":
                return evt.get("cc_agent")
    return None
